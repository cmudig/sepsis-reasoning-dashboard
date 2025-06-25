<script lang="ts">
  import { getContext } from 'svelte';
  import type { Writable } from 'svelte/store';
  import type { Explanation, PatientData } from '../patientdata';
  import Fa from 'svelte-fa';
  import {
    faBedPulse,
    faChevronDown,
    faChevronRight,
    faChevronUp,
  } from '@fortawesome/free-solid-svg-icons';
  import * as d3 from 'd3';
  import Tooltip from '../utils/Tooltip.svelte';
  import ExplanationGrid from './ExplanationGrid.svelte';

  export let colorScale = d3.interpolateTurbo;

  export let showSummary: boolean = true;
  export let collapsible: boolean = true;
  export let showExplanation: boolean = true;
  let explanationCollapsed: boolean = true;

  export let collapsed: boolean = collapsible;
  $: if (!collapsible) collapsed = false;

  let patientData: Writable<PatientData> = getContext('patientData');
  let timestepIndex: Writable<number> = getContext('timestepIndex');

  let explanation: { similar: Explanation[]; different: Explanation[] } | null =
    null;
  $: if (!!$patientData && !!$patientData['descriptive']) {
    explanation = $patientData['descriptive'].timesteps![$timestepIndex].data;
  } else {
    explanation = null;
  }
</script>

{#if !!explanation}
  <div class="w-full rounded-md bg-blue-50 p-4">
    <div class="flex items-center w-full gap-4">
      <div class="text-blue-700 flex-auto">
        <Fa icon={faBedPulse} class="inline mr-2" /><span
          class="font-bold uppercase font-mono mr-2">Sepsis AI</span
        >
        Similar and Different Patient Features <Tooltip
          hoverTargetClass="inline text-blue-700 hover:opacity-50 px-1"
          title="This AI presents features from the patient's clinical data that make it similar to other cases, and features that make it unusual."
        />
      </div>
      {#if showSummary}
        <div class="text-sm">
          {explanation.similar.length} similar, {explanation.different.length} different
        </div>
      {/if}
      {#if collapsible}
        <button
          class="hover:opacity-50 text-blue-700 shrink-0"
          on:click={() => (collapsed = !collapsed)}
        >
          <Fa icon={collapsed ? faChevronDown : faChevronUp} />
        </button>
      {/if}
    </div>
    {#if !collapsed}
      <div class="mt-2 measure">
        Sepsis AI found that this patient is <strong>similar</strong> to a cohort
        of other patients that often share these features:
      </div>

      <ExplanationGrid explanation={explanation.similar} />

      <div class="mt-2 measure">
        Meanwhile, this patient could be <strong>unusual</strong> because of the
        following features:
      </div>

      <ExplanationGrid explanation={explanation.different} />
      {#if showExplanation}
        <div class="rounded-md border border-blue-200 p-4 my-4 bg-white">
          <button
            class="flex items-center w-full gap-2 text-left hover:opacity-50"
            on:click={() => (explanationCollapsed = !explanationCollapsed)}
          >
            <Fa
              icon={explanationCollapsed ? faChevronRight : faChevronDown}
              class="text-sm"
            />
            <div class="italic">
              Why is Sepsis AI highlighting these features?
            </div>
          </button>
          {#if !explanationCollapsed}
            <div class="mt-4 text-sm measure">
              The AI system compared this patient's data to data from 100 other
              patients considered by the AI to be similar to this one,
              incorporating all of the data in the left part of the interface.
              Features rated as "similar" are more common in this patient group
              relative to average patients, while features rated as "unusual"
              are true in this patient but rare among similar patients.
            </div>
          {/if}
        </div>
      {/if}
    {/if}
  </div>
{/if}
