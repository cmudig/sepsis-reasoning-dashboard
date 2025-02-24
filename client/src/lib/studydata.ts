export type Stimulus = {
  ads: string;
  dataset: string;
  id: number;
  pseudonym: string;
  ts: number;
  vignette: string;
};
export type StudyProtocol = {
  text: {
    consent?: string;
    intro_text?: string;
    pre_survey_link?: string;
    post_patient_items?: {
      question: string;
      answer_instruction?: string;
      ads_only?: boolean;
    }[];
    prompt_text?: string;
  };
  patients: Stimulus[];
  dev_mode?: boolean;
};
