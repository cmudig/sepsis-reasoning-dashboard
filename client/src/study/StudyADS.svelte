<script lang="ts">
  import DescriptivePane from '../lib/rst/DescriptivePane.svelte';
  import PredictiveIndependentPane from '../lib/rst/PredictiveIndependentPane.svelte';
  import PredictionDependentPane from '../lib/rst/PredictionDependentPane.svelte';
  import PrescriptivePeerPane from '../lib/rst/PrescriptivePeerPane.svelte';
  import AiClinicianPane from '../lib/rst/AIClinicianPane.svelte';
  import type { Stimulus, StudyProtocol } from '../lib/studydata';
  import { setContext } from 'svelte';
  import { writable, type Writable } from 'svelte/store';
  import type { PatientData } from '../lib/patientdata';

  export let patientData: Writable<PatientData> = writable({});
  setContext('patientData', patientData);

  export let timestepIndex: Writable<number> = writable(0);
  setContext('timestepIndex', timestepIndex);

  export let studyProtocol: StudyProtocol | null = null;
  export let currentStimulus: Stimulus | null = null;

  export let showPrompt: boolean = true;
</script>

{#if !!currentStimulus && !!studyProtocol}
  <div class="mb-2 font-bold">{currentStimulus.pseudonym}</div>
  <div class="mb-4 leading-relaxed text-sm">{currentStimulus.vignette}</div>
  {#if showPrompt && !!studyProtocol && studyProtocol.text?.prompt_text}
    <div class="mb-4 font-bold">{studyProtocol.text.prompt_text}</div>
  {/if}
  {#if currentStimulus.ads == 'descriptive'}
    <div class="mb-4">
      <DescriptivePane collapsible={false} showSummary={false} />
    </div>
  {/if}
  {#if currentStimulus.ads == 'predictive_vaso_independent'}
    <div class="mb-4">
      <PredictiveIndependentPane
        shortName="vaso"
        longName="Vasopressor Requirement"
        outcomeDescription="still require vasopressors after 12 hours"
        collapsible={false}
        showGroundTruth={false}
        showSummary={false}
      />
    </div>
  {/if}
  {#if currentStimulus.ads == 'predictive_morta_independent'}
    <div class="mb-4">
      <PredictiveIndependentPane
        shortName="morta"
        longName="Mortality"
        outcomeDescription="have a final discharge outcome of mortality"
        collapsible={false}
        showGroundTruth={false}
        showSummary={false}
      />
    </div>
  {/if}
  {#if currentStimulus.ads == 'predictive_vaso_dependent'}
    <div class="mb-4">
      <PredictionDependentPane
        shortName="vaso"
        longName="Vasopressor Requirement"
        outcomeDescription="still require vasopressors after 12 hours"
        collapsible={false}
        showGroundTruth={false}
        showSummary={false}
      />
    </div>
  {/if}
  {#if currentStimulus.ads == 'predictive_morta_dependent'}
    <div class="mb-4">
      <PredictionDependentPane
        shortName="morta"
        longName="Mortality"
        outcomeDescription="have a final discharge outcome of mortality"
        collapsible={false}
        showGroundTruth={false}
        showSummary={false}
      />
    </div>
  {/if}
  {#if currentStimulus.ads == 'prescriptive_peer'}
    <div class="mb-4">
      <PrescriptivePeerPane
        collapsible={false}
        showGroundTruth={false}
        showSummary={false}
      />
    </div>
  {/if}
  {#if currentStimulus.ads == 'prescriptive_outcome'}
    <div class="mb-4">
      <AiClinicianPane
        collapsible={false}
        showGroundTruth={false}
        showSummary={false}
      />
    </div>
  {/if}
{/if}
