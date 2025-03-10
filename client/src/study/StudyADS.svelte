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
  import { formatText } from '../lib/utils/utils';
  import Fa from 'svelte-fa';
  import {
    faChevronDown,
    faChevronUp,
  } from '@fortawesome/free-solid-svg-icons';

  export let patientData: Writable<PatientData> = writable({});
  setContext('patientData', patientData);

  export let timestepIndex: Writable<number> = writable(0);
  setContext('timestepIndex', timestepIndex);

  export let studyProtocol: StudyProtocol | null = null;
  export let currentStimulus: Stimulus | null = null;

  export let showPrompt: boolean = true;

  let vignetteExpanded: boolean = false;

  $: if (!!currentStimulus) vignetteExpanded = false;
</script>

{#if !!currentStimulus && !!studyProtocol}
  <div class="mb-2 font-bold">{currentStimulus.pseudonym}</div>
  <div
    class="mb-2 leading-relaxed text-sm"
    class:line-clamp-3={!vignetteExpanded}
  >
    {@html formatText(currentStimulus.vignette)}
  </div>
  <button
    class="text-sm text-blue-600 hover:opacity-50 mb-4"
    on:click={() => (vignetteExpanded = !vignetteExpanded)}
    >{#if vignetteExpanded}<Fa icon={faChevronUp} class="inline mr-2" /> Hide patient
      summary{:else}<Fa icon={faChevronDown} class="inline mr-2" /> Expand patient
      summary...{/if}</button
  >
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
        outcomeDescription="require vasopressors after 12 hours"
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
        outcomeDescription="require vasopressors after 12 hours"
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
  {#if showPrompt && !!studyProtocol && studyProtocol.text?.prompt_text}
    <div class="mb-4">
      {@html formatText(studyProtocol.text.prompt_text)}
    </div>
  {/if}
{/if}
