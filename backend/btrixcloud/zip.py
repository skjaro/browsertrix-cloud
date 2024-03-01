"""
Methods for interacting with zip/WACZ files
"""

import io
import struct
import zipfile
import zlib

import aiohttp


# ============================================================================
EOCD_RECORD_SIZE = 22
ZIP64_EOCD_RECORD_SIZE = 56
ZIP64_EOCD_LOCATOR_SIZE = 20

MAX_STANDARD_ZIP_SIZE = 4_294_967_295

CHUNK_SIZE = 1024 * 256


# ============================================================================
def sync_get_filestream(client, bucket, key, file_zipinfo, cd_start):
    """Return uncompressed byte stream of file in WACZ"""
    # pylint: disable=too-many-locals
    file_head = sync_fetch(
        client, bucket, key, cd_start + file_zipinfo.header_offset + 26, 4
    )
    name_len = parse_little_endian_to_int(file_head[0:2])
    extra_len = parse_little_endian_to_int(file_head[2:4])

    content = sync_fetch_stream(
        client,
        bucket,
        key,
        cd_start + file_zipinfo.header_offset + 30 + name_len + extra_len,
        file_zipinfo.compress_size,
    )

    decompress = False
    if file_zipinfo.compress_type == zipfile.ZIP_DEFLATED:
        decompress = True

    return sync_iter_lines(content, decompress=decompress)


async def get_filestream_aiohttp(url, file_zipinfo, cd_start):
    """Return uncompressed byte stream of file in WACZ"""
    # pylint: disable=too-many-locals
    file_head = await fetch_aiohttp(url, cd_start + file_zipinfo.header_offset + 26, 4)
    name_len = parse_little_endian_to_int(file_head[0:2])
    extra_len = parse_little_endian_to_int(file_head[2:4])

    decompress = False
    if file_zipinfo.compress_type == zipfile.ZIP_DEFLATED:
        decompress = True

    pending = b""

    async for chunk in fetch_stream_aiohttp(
        url,
        cd_start + file_zipinfo.header_offset + 30 + name_len + extra_len,
        file_zipinfo.compress_size,
    ):
        if decompress:
            chunk = zlib.decompressobj(-zlib.MAX_WBITS).decompress(chunk)
        lines = (pending + chunk).splitlines(True)
        for line in lines[:-1]:
            print("line size", len(line), flush=True)
            yield line.splitlines(True)[0]
        pending = lines[-1]
        print("line size", len(pending), flush=True)

    if pending:
        yield pending.splitlines(True)[0]


def sync_iter_lines(chunk_iter, decompress=False, keepends=True):
    """
    Iter by lines, adapted from botocore
    """
    pending = b""
    for chunk in chunk_iter:
        if decompress:
            chunk = zlib.decompressobj(-zlib.MAX_WBITS).decompress(chunk)
        lines = (pending + chunk).splitlines(True)
        for line in lines[:-1]:
            yield line.splitlines(keepends)[0]
        pending = lines[-1]
    if pending:
        yield pending.splitlines(keepends)[0]


async def get_zip_file(client, bucket, key):
    """Fetch enough of the WACZ file be able to read the zip filelist"""
    file_size = await get_file_size(client, bucket, key)
    eocd_record = await fetch(
        client, bucket, key, file_size - EOCD_RECORD_SIZE, EOCD_RECORD_SIZE
    )

    if file_size <= MAX_STANDARD_ZIP_SIZE:
        cd_start, cd_size = get_central_directory_metadata_from_eocd(eocd_record)
        central_directory = await fetch(client, bucket, key, cd_start, cd_size)
        return (
            cd_start,
            zipfile.ZipFile(io.BytesIO(central_directory + eocd_record)),
        )

    zip64_eocd_record = await fetch(
        client,
        bucket,
        key,
        file_size
        - (EOCD_RECORD_SIZE + ZIP64_EOCD_LOCATOR_SIZE + ZIP64_EOCD_RECORD_SIZE),
        ZIP64_EOCD_RECORD_SIZE,
    )
    zip64_eocd_locator = await fetch(
        client,
        bucket,
        key,
        file_size - (EOCD_RECORD_SIZE + ZIP64_EOCD_LOCATOR_SIZE),
        ZIP64_EOCD_LOCATOR_SIZE,
    )
    cd_start, cd_size = get_central_directory_metadata_from_eocd64(zip64_eocd_record)
    central_directory = await fetch(client, bucket, key, cd_start, cd_size)
    return (
        cd_start,
        zipfile.ZipFile(
            io.BytesIO(
                central_directory + zip64_eocd_record + zip64_eocd_locator + eocd_record
            )
        ),
    )


async def get_zip_file_from_presigned_url(url: str):
    """Fetch enough of the WACZ file be able to read the zip filelist"""
    file_size = await get_file_size_presigned_url(url)
    eocd_record = await fetch_aiohttp(
        url, file_size - EOCD_RECORD_SIZE, EOCD_RECORD_SIZE
    )

    if file_size <= MAX_STANDARD_ZIP_SIZE:
        cd_start, cd_size = get_central_directory_metadata_from_eocd(eocd_record)
        if cd_start > 0 and cd_start < file_size:
            central_directory = await fetch_aiohttp(url, cd_start, cd_size)
            return (
                cd_start,
                zipfile.ZipFile(io.BytesIO(central_directory + eocd_record)),
            )

    zip64_eocd_record = await fetch_aiohttp(
        url,
        file_size
        - (EOCD_RECORD_SIZE + ZIP64_EOCD_LOCATOR_SIZE + ZIP64_EOCD_RECORD_SIZE),
        ZIP64_EOCD_RECORD_SIZE,
    )
    zip64_eocd_locator = await fetch_aiohttp(
        url,
        file_size - (EOCD_RECORD_SIZE + ZIP64_EOCD_LOCATOR_SIZE),
        ZIP64_EOCD_LOCATOR_SIZE,
    )
    cd_start, cd_size = get_central_directory_metadata_from_eocd64(zip64_eocd_record)
    if cd_start < 0 or cd_start > file_size:
        raise Exception("Invalid Zip")

    central_directory = await fetch_aiohttp(url, cd_start, cd_size)
    return (
        cd_start,
        zipfile.ZipFile(
            io.BytesIO(
                central_directory + zip64_eocd_record + zip64_eocd_locator + eocd_record
            )
        ),
    )


def sync_get_zip_file(client, bucket, key):
    """Fetch enough of the WACZ file be able to read the zip filelist"""
    file_size = sync_get_file_size(client, bucket, key)
    eocd_record = sync_fetch(
        client, bucket, key, file_size - EOCD_RECORD_SIZE, EOCD_RECORD_SIZE
    )

    if file_size <= MAX_STANDARD_ZIP_SIZE:
        cd_start, cd_size = get_central_directory_metadata_from_eocd(eocd_record)
        central_directory = sync_fetch(client, bucket, key, cd_start, cd_size)
        with zipfile.ZipFile(io.BytesIO(central_directory + eocd_record)) as zip_file:
            return (cd_start, zip_file)

    zip64_eocd_record = sync_fetch(
        client,
        bucket,
        key,
        file_size
        - (EOCD_RECORD_SIZE + ZIP64_EOCD_LOCATOR_SIZE + ZIP64_EOCD_RECORD_SIZE),
        ZIP64_EOCD_RECORD_SIZE,
    )
    zip64_eocd_locator = sync_fetch(
        client,
        bucket,
        key,
        file_size - (EOCD_RECORD_SIZE + ZIP64_EOCD_LOCATOR_SIZE),
        ZIP64_EOCD_LOCATOR_SIZE,
    )
    cd_start, cd_size = get_central_directory_metadata_from_eocd64(zip64_eocd_record)
    central_directory = sync_fetch(client, bucket, key, cd_start, cd_size)
    with zipfile.ZipFile(
        io.BytesIO(
            central_directory + zip64_eocd_record + zip64_eocd_locator + eocd_record
        )
    ) as zip_file:
        return (cd_start, zip_file)


async def get_file_size_presigned_url(url: str):
    """Get file size from presigned url"""
    headers = {"Range": "bytes=0-1"}
    if "host.docker.internal" in url:
        headers["Host"] = "localhost:30870"

    length = 0
    async with aiohttp.ClientSession() as client:
        async with client.get(url, headers=headers) as resp:
            cr = resp.headers.get("Content-Range")
            if cr:
                length = int(cr.split("/")[1])

    print("WACZ length", length, url, flush=True)
    return length


async def get_file_size(client, bucket, key):
    """Get WACZ file size from HEAD request"""
    head_response = await client.head_object(Bucket=bucket, Key=key)
    return head_response["ContentLength"]


def sync_get_file_size(client, bucket, key):
    """Get WACZ file size from HEAD request"""
    head_response = client.head_object(Bucket=bucket, Key=key)
    return head_response["ContentLength"]


async def fetch_aiohttp(url, start, length):
    """Fetch a byte range from a file in object storage"""
    end = start + length - 1
    headers = {"Range": f"bytes={start}-{end}"}
    if "host.docker.internal" in url:
        headers["Host"] = "localhost:30870"

    print(f"Fetching chunk: {length}")

    async with aiohttp.ClientSession() as client:
        async with client.get(url, headers=headers) as resp:
            return await resp.read()


async def fetch(client, bucket, key, start, length):
    """Fetch a byte range from a file in object storage"""
    end = start + length - 1
    response = await client.get_object(
        Bucket=bucket, Key=key, Range=f"bytes={start}-{end}"
    )
    return await response["Body"].read()


def sync_fetch(client, bucket, key, start, length):
    """Fetch a byte range from a file in object storage"""
    end = start + length - 1
    response = client.get_object(Bucket=bucket, Key=key, Range=f"bytes={start}-{end}")
    return response["Body"].read()


def sync_fetch_stream(client, bucket, key, start, length):
    """Fetch a byte range from a file in object storage as a stream"""
    end = start + length - 1
    response = client.get_object(Bucket=bucket, Key=key, Range=f"bytes={start}-{end}")
    return response["Body"].iter_chunks(chunk_size=CHUNK_SIZE)


async def fetch_stream_aiohttp(url, start, length):
    """Fetch a byte range from a presigned url as a stream"""
    end = start + length - 1
    headers = {"Range": f"bytes={start}-{end}"}

    print("Fetch stream", length, flush=True)

    async with aiohttp.ClientSession() as client:
        async with client.get(url, headers=headers) as resp:
            async for chunk, _ in resp.content.iter_chunks():
                print("Chunk size", len(chunk), flush=True)
                yield chunk


def get_central_directory_metadata_from_eocd(eocd):
    """Get central directory start and size"""
    cd_size = parse_little_endian_to_int(eocd[12:16])
    cd_start = parse_little_endian_to_int(eocd[16:20])
    return cd_start, cd_size


def get_central_directory_metadata_from_eocd64(eocd64):
    """Get central directory start and size for zip64"""
    cd_size = parse_little_endian_to_int(eocd64[40:48])
    cd_start = parse_little_endian_to_int(eocd64[48:56])
    return cd_start, cd_size


def parse_little_endian_to_int(little_endian_bytes):
    """Convert little endian used in zip spec to int"""
    byte_length = len(little_endian_bytes)
    format_character = "q"
    if byte_length == 4:
        format_character = "i"
    elif byte_length == 2:
        format_character = "h"

    return struct.unpack("<" + format_character, little_endian_bytes)[0]
