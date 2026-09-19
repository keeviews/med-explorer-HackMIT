export type Suggestion = {
  id: number
  drug_name: string
  rxnorm_id: string | null
  indication_snippet: string
  matched_condition: string | null
  source: string
  data_label: string
  score: number
}

export type SuggestResponse = {
  query: string
  disclaimer: string
  data_notice: string
  result_count: number
  results: Suggestion[]
}

export type ConditionSummary = {
  name: string
  aliases: string[]
}

export type ConditionsResponse = {
  disclaimer: string
  data_notice: string
  conditions: ConditionSummary[]
}

export type DrugDetail = {
  id: number
  drug_name: string
  rxnorm_id: string | null
  drug_class: string | null
  route: string | null
  rx_otc: string | null
  common_side_effects: string[]
  typical_use_note: string | null
  monitoring_note: string | null
  linked_conditions: string[]
  data_label: string
}

export type ComparePick = {
  id: number
  name: string
}

export type Similarity = {
  field: string
  value: string
  drug_ids: number[]
  drug_names: string[]
}

export type CombinationAlert = {
  severity: "urgent_seed" | "discuss" | string
  code: string
  title: string
  detail: string
  talk_with_clinician: string
  drug_ids: number[]
  drug_names: string[]
  fields: string[]
  data_label: string
}

export type CompareResponse = {
  disclaimer: string
  data_notice: string
  compare_note: string
  overlap_note: string
  talk_with_clinician: string
  compare_limit: number
  result_count: number
  drugs: DrugDetail[]
  similarities: Similarity[]
  alerts: CombinationAlert[]
  overlap_summary: string | null
}

export type MedicineNote = {
  id: number
  name: string
  addedAt: string
  stoppedAt?: string
  source?: string
  fhir_name?: string | null
}

export type UnmappedMedication = {
  name: string
  rxnorm_id?: string | null
  source?: string
}

export type MyChartStatus = {
  disclaimer: string
  configured: boolean
  authorize_url: string | null
  redirect_uri: string
  fhir_base: string
  setup_note: string
  demo_available: boolean
}

export type FhirImportResponse = {
  disclaimer: string
  data_notice: string
  source: string
  mapped: Array<{
    id: number
    name: string
    rxnorm_id: string | null
    fhir_name: string | null
    source: string
  }>
  unmapped: UnmappedMedication[]
  mapped_count: number
  unmapped_count: number
}

export type ScanCandidate = {
  id: number
  name: string
  strength: string | null
  form: string | null
  confidence: number
}

export type MedicineScanResponse = {
  disclaimer: string
  mode: "demo" | "ocr"
  notice: string
  raw_text: string
  candidates: ScanCandidate[]
}

export class ApiError extends Error {
  status?: number
}
