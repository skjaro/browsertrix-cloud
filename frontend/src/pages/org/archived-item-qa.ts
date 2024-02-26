import {
  html,
  css,
  nothing,
  type PropertyValues,
  type TemplateResult,
} from "lit";
import { state, property, customElement } from "lit/decorators.js";
import { msg, localized } from "@lit/localize";

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
          <nav>
            <btrix-navigation-button
              id="screenshot-tab"
              href=${`${crawlBaseUrl}/review/screenshots`}
              .active=${this.tab === "screenshots"}
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
          <div role="region" aria-labelledby="${this.tab}-tab">
            ${this.renderSections()}
          </div>
        </section>
        <h2 class="pageListHeader outline">
          ${msg("Pages List")} <sl-button>${msg("Finish Review")}</sl-button>
        </h2>
        <section class="pageList outline">[page list]</section>
      </article>
    `;
  }

  private renderSections() {
    const tabSection: Record<
      QATab,
      { label: string; render: () => TemplateResult<1> | undefined }
    > = {
      screenshots: {
        label: msg("Screenshots"),
        render: this.renderScreenshots,
      },
      replay: {
        label: msg("Replay"),
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
            aria-hidden=${!isActive}
          >
            ${section.render()}
          </section>
        `;
      })}
    `;
  }

  private readonly renderScreenshots = () => {
    return html`[screenshots]`;
  };

  private readonly renderReplay = () => {
    if (!this.itemId) return;
    const replaySource = `/api/orgs/${this.orgId}/crawls/${this.itemId}/replay.json`;
    const headers = this.authState?.headers;
    const config = JSON.stringify({ headers });

    return html`<div id="replay-crawl" class="aspect-4/3 overflow-hidden">
      <replay-web-page
        source="${replaySource}"
        coll="${this.itemId}"
        config="${config}"
        replayBase="/replay/"
        noSandbox="true"
        noCache="true"
      ></replay-web-page>
    </div>`;
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
    const apiPath = `/orgs/${this.orgId}/all-crawls/${this.itemId}`;
    return this.api.fetch<ArchivedItem>(apiPath, this.authState!);
  }
}
