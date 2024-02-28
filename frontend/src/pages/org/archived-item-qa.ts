import {
  html,
  css,
  nothing,
  type PropertyValues,
  type TemplateResult,
} from "lit";
import { state, property, customElement } from "lit/decorators.js";
import { msg, localized } from "@lit/localize";
import { choose } from "lit/directives/choose.js";

import { TailwindElement } from "@/classes/TailwindElement";
import { type AuthState } from "@/utils/AuthService";
import { TWO_COL_SCREEN_MIN_CSS } from "@/components/ui/tab-list";
import { NavigateController } from "@/controllers/navigate";
import { APIController } from "@/controllers/api";
import { NotifyController } from "@/controllers/notify";
import { renderName } from "@/utils/crawler";
import { type ArchivedItem } from "@/types/crawler";

const TABS = ["screenshots", "replay"] as const;
export type QATab = (typeof TABS)[number];

@localized()
@customElement("btrix-archived-item-qa")
export class ArchivedItemQA extends TailwindElement {
  static styles = css`
    :host {
      height: inherit;
      display: flex;
      flex-direction: column;
    }

    article {
      flex-grow: 1;
      display: grid;
      grid-gap: 1rem;
      grid-template:
        "mainHeader"
        "main"
        "pageListHeader"
        "pageList";
      grid-template-rows: repeat(4, max-content);
    }

    @media only screen and (min-width: ${TWO_COL_SCREEN_MIN_CSS}) {
      article {
        grid-template:
          "mainHeader pageListHeader"
          "main pageList";
        grid-template-columns: 1fr 24rem;
        grid-template-rows: min-content 1fr;
      }
    }

    .mainHeader {
      grid-area: mainHeader;
    }

    .pageListHeader {
      grid-area: pageListHeader;
    }

    .main {
      grid-area: main;
    }

    .pageList {
      grid-area: pageList;
    }
  `;

  @property({ type: Object })
  authState?: AuthState;

  @property({ type: String })
  orgId?: string;

  @property({ type: String })
  itemId?: string;

  @property({ type: Boolean })
  isCrawler = false;

  @property({ type: String })
  tab: QATab = "screenshots";

  @state()
  private item?: ArchivedItem;

  @state()
  private screenshotIframesReady: 0 | 1 | 2 = 0;

  private readonly api = new APIController(this);
  private readonly navigate = new NavigateController(this);
  private readonly notify = new NotifyController(this);

  protected willUpdate(
    changedProperties: PropertyValues<this> | Map<PropertyKey, unknown>,
  ): void {
    if (changedProperties.has("itemId") && this.itemId) {
      void this.fetchArchivedItem();
    }
  }

  render() {
    const crawlBaseUrl = `${this.navigate.orgBasePath}/items/crawl/${this.itemId}`;
    const itemName = this.item ? renderName(this.item) : nothing;
    return html`
      <nav class="mb-7">
        <a
          class="text-sm font-medium text-neutral-500 hover:text-neutral-600"
          href=${`${crawlBaseUrl}`}
          @click=${this.navigate.link}
        >
          <sl-icon
            name="arrow-left"
            class="inline-block align-middle"
          ></sl-icon>
          <span class="inline-block align-middle">
            ${msg("Back to")} ${itemName}
          </span>
        </a>
      </nav>

      <article>
        <header class="mainHeader outline">
          <h1>${msg("Review")} &mdash; ${itemName}</h1>
        </header>
        <section class="main outline">
          <nav aria-label=${msg("QA page")}>
            <btrix-navigation-button
              id="screenshot-tab"
              href=${`${crawlBaseUrl}/review/screenshots`}
              ?active=${this.tab === "screenshots"}
              size="small"
              @click=${this.navigate.link}
              >${msg("Screenshots")}</btrix-navigation-button
            >
            <btrix-navigation-button
              id="replay-tab"
              href=${`${crawlBaseUrl}/review/replay`}
              .active=${this.tab === "replay"}
              size="small"
              @click=${this.navigate.link}
              >${msg("Replay")}</btrix-navigation-button
            >
          </nav>
          ${this.renderToolbar()} ${this.renderSections()}
        </section>
        <h2 class="pageListHeader outline">
          ${msg("Pages List")} <sl-button>${msg("Finish Review")}</sl-button>
        </h2>
        <section class="pageList outline">[page list]</section>
      </article>
    `;
  }

  private renderToolbar() {
    return html`
      <div
        class="my-2 flex h-12 items-center rounded-md border bg-neutral-50 text-base"
      >
        <div class="mx-1">
          ${choose(this.tab, [
            [
              "replay",
              () => html`
                <!-- <sl-icon-button name="arrow-clockwise"></sl-icon-button> -->
              `,
            ],
            [
              "screenshots",
              () => html`
                <!-- <sl-icon-button name="intersect"></sl-icon-button> -->
                <!-- <sl-icon-button name="layout-split"></sl-icon-button> -->
                <!-- <sl-icon-button name="vr"></sl-icon-button> -->
              `,
            ],
          ])}
        </div>
        <div
          class=" mx-1.5 flex-1 rounded border bg-neutral-0 p-2 text-sm leading-none"
        >
          https://example.com
        </div>
      </div>
    `;
  }

  private renderSections() {
    const tabSection: Record<
      QATab,
      { render: () => TemplateResult<1> | undefined }
    > = {
      screenshots: {
        render: this.renderScreenshots,
      },
      replay: {
        render: this.renderReplay,
      },
    };
    return html`
      ${TABS.map((tab) => {
        const section = tabSection[tab];
        const isActive = tab === this.tab;
        return html`
          <section
            class="${isActive ? "" : "invisible absolute -top-full -left-full"}"
            aria-labelledby="${this.tab}-tab"
            aria-hidden=${!isActive}
          >
            ${section.render()}
          </section>
        `;
      })}
    `;
  }

  private readonly renderScreenshots = () => {
    if (!this.itemId) return;

    const url = `/replay/w/manual-20240226234726-051ed881-37e/:fbc91e679056dc8da1528376ddbc7e5c931ca9b03a0d0f65430c5ee2a76c94c2/20240226234908mp_/urn:view:http://example.com/`;

    return html`
      <div class="mb-2 flex justify-between text-base font-medium">
        <h3 id="crawlScreenshotHeading">${msg("Crawl Screenshot")}</h3>
        <h3 id="replayScreenshotHeading">${msg("Replay Screenshot")}</h3>
      </div>
      <div class="overflow-hidden rounded border bg-slate-50">
        <sl-image-comparer
          class="${this.screenshotIframesReady === 2
            ? "visible"
            : "invisible"} w-full"
        >
          <iframe
            slot="before"
            name="crawlScreenshot"
            src="${url}"
            class="aspect-video w-full"
            aria-labelledby="crawlScreenshotHeading"
            @load=${this.onScreenshotLoad}
          ></iframe>
          <iframe
            slot="after"
            name="replayScreenshot"
            src="${url}"
            class="aspect-video w-full"
            aria-labelledby="replayScreenshotHeading"
            @load=${this.onScreenshotLoad}
          ></iframe>
        </sl-image-comparer>
      </div>
    `;
  };

  private readonly renderReplay = (crawlId?: string) => {
    if (!this.itemId) return;
    const replaySource = `/api/orgs/${this.orgId}/crawls/${crawlId || this.itemId}/replay.json`;
    const headers = this.authState?.headers;
    const config = JSON.stringify({ headers });

    return html`<div class="aspect-4/3 overflow-hidden">
      <replay-web-page
        source="${replaySource}"
        coll="${this.itemId}"
        config="${config}"
        replayBase="/replay/"
        embed="replayonly"
        noCache="true"
      ></replay-web-page>
    </div>`;
  };

  private readonly onScreenshotLoad = (e: Event) => {
    const iframe = e.currentTarget as HTMLIFrameElement;
    const img = iframe.contentDocument?.body.querySelector("img");
    // Make image fill iframe container
    if (img) {
      img.style.height = "auto";
      img.style.width = "100%";
    }
    this.screenshotIframesReady += 1;
  };

  private async fetchArchivedItem(): Promise<void> {
    try {
      this.item = await this.getArchivedItem();
    } catch {
      this.notify.toast({
        message: msg("Sorry, couldn't retrieve archived item at this time."),
        variant: "danger",
        icon: "exclamation-octagon",
      });
    }
  }

  private async getArchivedItem(): Promise<ArchivedItem> {
    const apiPath = `/orgs/${this.orgId}/crawls/${this.itemId}`;
    return this.api.fetch<ArchivedItem>(apiPath, this.authState!);
  }
}
