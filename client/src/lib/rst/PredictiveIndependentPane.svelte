<script lang="ts">
  import { getContext } from 'svelte';
  import type { Writable } from 'svelte/store';
  import type { PatientData } from '../patientdata';
  import Fa from 'svelte-fa';
  import {
    faBedPulse,
    faChevronDown,
    faChevronRight,
    faChevronUp,
  } from '@fortawesome/free-solid-svg-icons';
  import * as d3 from 'd3';
  import Tooltip from '../utils/Tooltip.svelte';

  export let shortName: string = '';
  export let longName: string = '';
  export let outcomeDescription: string = '';

  export let showGroundTruth: boolean = true;
  export let showSummary: boolean = true;
  export let collapsible: boolean = true;

  export let collapsed: boolean = collapsible;
  $: if (!collapsible) collapsed = false;

  // export let colorScale = d3.interpolateTurbo;

  type Prediction = {
    prediction: string;
    base_rate_comparison?: string;
    prediction_percentage: number;
    base_rate_percentage: number;
    ground_truth?: string;
    severity_range: {
      min: number;
      max: number;
    };
  };

  let patientData: Writable<PatientData> = getContext('patientData');
  let timestepIndex: Writable<number> = getContext('timestepIndex');

  let prediction: Prediction | undefined;
  $: if (
    !!$patientData &&
    !!shortName &&
    !!$patientData[`predictive_${shortName}_independent`]
  ) {
    prediction =
      $patientData[`predictive_${shortName}_independent`].timesteps![
        $timestepIndex
      ].data;
  } else {
    prediction = undefined;
  }
</script>

{#if !!prediction}
  <div class="w-full rounded-md bg-blue-50 p-4">
    <div class="flex items-center w-full gap-4">
      <div class="text-blue-700 flex-auto">
        <Fa icon={faBedPulse} class="inline mr-2" /><span
          class="font-bold uppercase font-mono mr-2">Sepsis AI</span
        >
        Risk of {longName}
      </div>
      {#if showSummary}
        <div class="text-sm">
          {prediction.prediction},
          {#if (prediction.prediction_percentage > 66 && prediction.ground_truth == 'Yes') || (prediction.prediction_percentage < 33 && prediction.ground_truth == 'No')}
            Accurate
          {:else if (prediction.prediction_percentage < 33 && prediction.ground_truth == 'Yes') || (prediction.prediction_percentage > 66 && prediction.ground_truth == 'No')}
            Inaccurate
          {:else}Inconclusive
          {/if}
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
        Sepsis AI predicts this patient is <Tooltip
          title="{prediction.prediction_percentage}% chance"
          ><span
            class="font-bold hoverable-text {prediction.prediction_percentage >
            66
              ? 'text-red-600'
              : prediction.prediction_percentage > 33
                ? 'text-yellow-600'
                : 'text-green-600'}">{prediction.prediction}</span
          ></Tooltip
        >
        to {outcomeDescription}{#if !!prediction.base_rate_comparison},
          {prediction.base_rate_comparison}
          compared to <Tooltip title="{prediction.base_rate_percentage}% chance"
            ><span class="hoverable-text">other patients</span></Tooltip
          > with a similar SOFA score{/if}.
      </div>

      {#if showGroundTruth && !!prediction.ground_truth}
        <div class="mt-4 text-sm text-blue-700">
          <strong>Ground Truth:</strong>
          {prediction.ground_truth}
        </div>
      {/if}
    {/if}
  </div>
{/if}
