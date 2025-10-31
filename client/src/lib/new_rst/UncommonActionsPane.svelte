<script lang="ts">
  import { getContext, onMount } from 'svelte';
  import type { Writable } from 'svelte/store';
  import type { Explanation, PatientData } from '../patientdata';
  import Fa from 'svelte-fa';
  import {
    faBedPulse,
    faChevronDown,
    faChevronRight,
    faChevronUp,
    faWarning,
  } from '@fortawesome/free-solid-svg-icons';
  import * as d3 from 'd3';
  import CategoryBar from '../charts/CategoryBar.svelte';
  import Tooltip from '../utils/Tooltip.svelte';
  import { fade } from 'svelte/transition';

  export let shortName: string = '';

  export let showGroundTruth: boolean = true;
  export let collapsible: boolean = true;

  export let collapsed: boolean = collapsible;
  $: if (!collapsible) collapsed = false;

  type ActionPrediction = {
    short_name: string;
    long_name: string;
    treatment_indexes: (number[] | null)[];
    count: number;
    prob: number;
  };
  type UncommonActionPrediction = {
    uncommon_actions: ActionPrediction[];
    ground_truth?: {
      tx: string;
      label: string;
    }[];
    severity_range: {
      min: number;
      max: number;
    };
    explanation?: Explanation[];
  };

  const TreatmentPolicyNames: { [key: string]: string[] } = {
    Volume: [
      '< 100 mL Fluids',
      '100 mL - 1 L Fluids',
      '> 1 L Fluids',
      'Diuretics',
    ],
    Vasopressors: ['None', 'One', 'Multiple'],
  };

  let patientData: Writable<PatientData> = getContext('patientData');
  let timestepIndex: Writable<number> = getContext('timestepIndex');

  // let visibleTarget: string = 'Mortality';

  let prediction: UncommonActionPrediction | undefined;
  $: if (!!$patientData && !!$patientData.uncommon_actions) {
    prediction = $patientData.uncommon_actions.timesteps![$timestepIndex].data;
  } else {
    prediction = undefined;
  }

  let sortedPredictions: ActionPrediction[] | undefined;
  $: if (!!prediction) {
    sortedPredictions = [...prediction.uncommon_actions];
    sortedPredictions.sort((a, b) => a.count - b.count);
    if (sortedPredictions.length > 3)
      sortedPredictions = sortedPredictions.slice(0, 3);
  } else {
    sortedPredictions = undefined;
  }

  const probabilityFormat = d3.format('.0~%');

  const replacePhrases: { [key: string]: string } = {
    '100 mL to 1 L': 'up to 1 L',
    '< 100 mL of': 'no',
  };

  function getActionLabel(actionName: string) {
    Object.entries(replacePhrases).forEach(
      ([pat, repl]) => (actionName = actionName.replaceAll(pat, repl))
    );
    return actionName;
  }

  let visible = false;
  onMount(() => {
    visible = true;
  });
</script>

{#if !!prediction && !!sortedPredictions}
  <div
    class="w-full rounded-[8px] p-0.5 bg-gradient-to-br from-blue-600 via-purple-500 to-rose-500"
  >
    <div class="w-full rounded-md bg-gray-50 p-4">
      <div class="flex items-center w-full gap-4">
        <div class="text-blue-600 flex-auto">
          <Fa icon={faBedPulse} class="inline mr-2" /><span
            class="inline-block font-bold bg-clip-text text-transparent bg-gradient-to-br from-blue-600 via-purple-500 to-rose-500 font-bold uppercase font-mono mr-2"
            >Sepsis AI</span
          >
        </div>
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
        {#if visible}
          <div class="mt-2 measure" in:fade>
            Sepsis AI found that the following treatment plans were rarely
            chosen by providers for similar patients and may be less suitable
            for this patient:
          </div>
        {/if}
        <div class="mt-4 space-y-2">
          {#each sortedPredictions as pred, i (i)}
            {#if visible}
              <div
                class="rounded-md bg-orange-100 border-2 border-orange-300 p-4 w-full flex justify-stretch items-center gap-4"
                in:fade={{ delay: i * 200 }}
              >
                <div class="text-orange-400/50 text-xl">
                  <Fa icon={faWarning} />
                </div>
                <div class="flex-auto w-0">
                  <div class="mb-1">
                    <strong>{getActionLabel(pred.long_name)}</strong>
                  </div>
                  <div class="text-sm text-orange-700">
                    {pred.count}/100 similar patients
                  </div>
                </div>
              </div>
            {/if}
          {/each}
        </div>
        {#if showGroundTruth && !!prediction.ground_truth}
          <div class="mt-4 text-sm text-blue-700">Ground truth:</div>
          {#each prediction.ground_truth as gt (gt.tx)}
            <div class="mt-2 text-sm">
              <span class="font-bold">{gt.tx}</span>: {gt.label}
            </div>
          {/each}
        {/if}
        {#if visible}
          <div class="mt-4 text-sm measure" in:fade>
            This prediction is based on prior clinicians' treatment decisions
            for 100 patients that Sepsis AI considers similar to this one in
            presentation, current status, and overall disease severity.
          </div>
        {/if}
      {/if}
    </div>
  </div>
{/if}
