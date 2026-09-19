export type LanguageMode = "simple" | "detailed"

export const COPY = {
  simple: {
    disclaimer:
      "Not medical advice. Talk with your doctor or nurse before you start, stop, or change any medicine.",
    headline: "Ask about medicines",
    intro: "Search a health problem. Compare a few options. Take questions to your visit.",
    myMedicines: "My medicines",
    searchPlaceholder: "High blood pressure, diabetes, migraine…",
    idleTitle: "Search a health problem to see medicines.",
    idleBody: "Try a button below. Information comes from U.S. FDA drug labels — it is not a prescription.",
    loading: "Searching…",
    errorTitle: "Search didn’t work.",
    emptyTitle: (q: string) => `Nothing found for “${q}”.`,
    emptyBody: "Try one of the buttons above.",
    resultsTitle: "Medicines",
    resultsCount: (n: number, q: string) => `${n} for “${q}”`,
    sampleData: "FDA label data",
    footer: "Not a doctor. Not a ranking. Ask your care team before changing medicines.",
    compareTitle: "Side by side",
    compareIntro: "Green = same. Red = ask your doctor before taking together.",
    compareEmptyTitle: "Pick at least two medicines.",
    compareEmptyBody: "Tap Compare on search results. You can pick up to four.",
    compareLoading: "Loading…",
    compareErrorTitle: "Couldn’t load the comparison.",
    takingThis: "I take this",
    onMyList: "On my list",
    addCompare: "Compare",
    removeCompare: "Remove",
    compareFull: "List full (4)",
    trayLabel: (n: number) => `Compare ${n}/4`,
    trayHint: "Green = same · Red = ask first",
    hideCompare: "Hide",
    showCompare: "Compare",
    myTitle: "My medicines",
    myIntro: "Saved on this phone or computer. Not sent to your clinic.",
    connectTitle: "Fill from MyChart",
    connectBody: "Sign in at MyChart to copy your list. We never ask for your password here.",
    signInMyChart: "Sign in with MyChart",
    loadDemo: "Try a sample list",
    currentlyTaking: "I’m taking",
    pastNotes: "Past",
    takingEmpty: "Add medicines from search, or load a sample list.",
    pastEmpty: "Nothing moved here yet.",
    movePast: "Move to past",
    backCurrent: "Move back",
    removeNote: "Remove",
    reviewList: "Check for overlap",
    reviewShort: "Add two medicines first.",
    reviewTitle: "Overlap check",
    reviewNone: "No overlap flagged in this sample. Still ask your doctor.",
    unmappedTitle: "Not in this app’s list yet",
    unmappedBody: "Still worth mentioning at your visit.",
    dismiss: "Hide",
    indication: "Used for",
    notListed: "Not listed",
    legendSame: "Same",
    legendAsk: "Ask first",
    alertUrgent: "Ask before combining",
    labelSays: "What the FDA label says",
    seeLabel: "See the FDA label",
    alertDiscuss: "Worth asking about",
    alertAsk: "Ask your doctor before changing anything.",
    importOk: (mapped: number, extra: number) =>
      extra
        ? `Added ${mapped}. ${extra} didn’t match this app’s list.`
        : `Added ${mapped} from the sample list.`,
    importDemoNote: "Sample list — not your real MyChart.",
    signInNeedsSetup: "Live MyChart sign-in isn’t set up on this computer yet.",
    rowClass: "Type",
    rowRoute: "How you take it",
    rowRx: "Rx or store-bought",
    rowUse: "Usual use",
    rowEffects: "Side effects",
    rowAsk: "Ask about",
    rowFor: "Also used for",
    onCurrent: "On my list",
    search: "Search",
    searchLabel: "Health problem",
    searchTooShort: "Type at least two letters.",
    searchFail: "Something went wrong. Try again.",
    clear: "Clear",
    medicinesCount: (n: number) => `${n} medicine${n === 1 ? "" : "s"}`,
    sampleBadge: "From FDA labels",
    topic: "Topic",
    sourceDemo: "Sample",
    sourceMyChart: "MyChart",
  },
  detailed: {
    disclaimer:
      "This tool is decision support only — not medical advice, a diagnosis, or a prescription. Do not start, stop, or change any medicine based on these results. Discuss them with a licensed clinician who knows your history.",
    headline: "Medicines to discuss with your clinician",
    intro:
      "Search a condition, compare a few options, and keep a private list of what you take. This is not a prescription or a ranking.",
    myMedicines: "My medicines",
    searchPlaceholder: "Hypertension, type 2 diabetes, GERD…",
    idleTitle: "Search a condition to see linked medicines.",
    idleBody:
      "Results come from U.S. FDA drug labels (openFDA), explained in plain language. They are not clinical guidelines.",
    loading: "Looking up medicines…",
    errorTitle: "We could not complete that search.",
    emptyTitle: (q: string) => `No medicines for “${q}” in this dataset.`,
    emptyBody: "Try one of the conditions above.",
    resultsTitle: "Linked medicines",
    resultsCount: (n: number, q: string) => `${n} for “${q}”`,
    sampleData: "FDA label data",
    footer:
      "Not a complete interaction checker. Compare is not a recommendation. MyChart uses patient sign-in at Epic, never a password typed here.",
    compareTitle: "Compare",
    compareIntro:
      "Green marks matching fields. Red marks flags for combinations to review with a clinician — not an order to stop a medicine.",
    compareEmptyTitle: "Add at least two medicines to compare.",
    compareEmptyBody: "Use Compare on search results. Up to four at a time.",
    compareLoading: "Loading…",
    compareErrorTitle: "Could not load that comparison.",
    takingThis: "I take this",
    onMyList: "On my list",
    addCompare: "Add to compare",
    removeCompare: "Remove",
    compareFull: "Compare list full (4)",
    trayLabel: (n: number) => `Compare ${n}/4`,
    trayHint: "Not a ranking",
    hideCompare: "Hide compare",
    showCompare: "Compare",
    myTitle: "My medicines",
    myIntro: "Stored in this browser only. Moving a medicine to Past does not mean you should stop it.",
    connectTitle: "Connect MyChart",
    connectBody:
      "Sign in at Epic / MyChart (SMART on FHIR) to copy medications. DiscussMeds never asks for your MyChart password.",
    signInMyChart: "Sign in with MyChart",
    loadDemo: "Load sample list",
    currentlyTaking: "Currently taking",
    pastNotes: "Past",
    takingEmpty: "Load a sample list, or tap “I take this” on a search result.",
    pastEmpty: "Medicines you move off the current list stay here.",
    movePast: "Move to past",
    backCurrent: "Move back",
    removeNote: "Remove",
    reviewList: "Check for overlap",
    reviewShort: "Add at least two current medicines first.",
    reviewTitle: "Overlap review",
    reviewNone: "No sample overlap flags for this set. That does not mean the list is safe. Ask your clinician.",
    unmappedTitle: "Imported but not in this dataset",
    unmappedBody: "Still worth mentioning to your clinician. They cannot enter compare yet.",
    dismiss: "Hide",
    indication: "Used for",
    notListed: "Not listed",
    legendSame: "Matching fields",
    legendAsk: "Combination flag",
    alertUrgent: "Flag — ask before combining",
    labelSays: "What the FDA label says",
    seeLabel: "See the FDA label",
    alertDiscuss: "Note — worth discussing",
    alertAsk: "Ask your clinician before changing anything.",
    importOk: (mapped: number, extra: number) =>
      extra
        ? `Imported ${mapped}. ${extra} not in this dataset. Sample list, not a live chart.`
        : `Imported ${mapped} from a sample FHIR list. Not a live MyChart chart.`,
    importDemoNote: "Sample FHIR list — not a live MyChart chart.",
    signInNeedsSetup: "Set EPIC_CLIENT_ID to enable live MyChart sign-in.",
    rowClass: "Drug class",
    rowRoute: "How it is taken",
    rowRx: "Rx or OTC",
    rowUse: "Typical use",
    rowEffects: "Common side effects",
    rowAsk: "Ask a clinician about",
    rowFor: "Also linked to",
    onCurrent: "On my list",
    search: "Search",
    searchLabel: "Condition",
    searchTooShort: "Type at least two characters to search a condition.",
    searchFail: "Something went wrong while searching.",
    clear: "Clear",
    medicinesCount: (n: number) => `${n} medicine${n === 1 ? "" : "s"}`,
    sampleBadge: "FDA label data",
    topic: "Topic",
    sourceDemo: "Demo FHIR",
    sourceMyChart: "MyChart",
  },
} as const

const SHORT_CONDITIONS: Record<string, string> = {
  Hypertension: "High blood pressure",
  "Type 2 diabetes mellitus": "Type 2 diabetes",
  "Seasonal allergic rhinitis": "Seasonal allergies",
  "Gastroesophageal reflux disease": "GERD",
  Migraine: "Migraine",
}

export function shortCondition(name: string, simple: boolean): string {
  if (!simple) return name
  return SHORT_CONDITIONS[name] ?? name
}

export function plainSeedNote(text: string, simple: boolean): string {
  if (!simple) return text
  const cleaned = text
    .replace(/\s*in this seed set\.?/gi, "")
    .replace(/\s*are commonly discussed with a clinician\.?/gi, "")
    .replace(/\s*is commonly discussed with a clinician\.?/gi, "")
    .replace(/\s*associated indication in seed data/gi, "")
    .replace(/\s*;\s*/g, ". ")
    .replace(/\s{2,}/g, " ")
    .trim()
    .replace(/[.;]+$/, "")
  return cleaned ? `${cleaned}.` : text
}

export function simpleAlertTitle(alert: { code: string; title: string }): string {
  const title = alert.title.toLowerCase()
  if (alert.code === "duplicate_class") return "Ask about taking more than one of this type"
  if (title.includes("ace") || title.includes("arb")) return "Ask before combining these two"
  if (title.includes("acid")) return "Ask about two stomach medicines"
  if (title.includes("migraine")) return "Ask about two migraine medicines"
  return "Ask your doctor about these together"
}

export function simpleAlertDetail(alert: { code: string; title: string }): string {
  const title = alert.title.toLowerCase()
  if (alert.code === "duplicate_class") return "Your doctor can say if you still need both."
  if (title.includes("ace") || title.includes("arb")) return "Both are used for blood pressure."
  if (title.includes("acid")) return "Both lower stomach acid."
  if (title.includes("migraine")) return "Your doctor can explain when to use each one."
  return "Ask before you change anything."
}
