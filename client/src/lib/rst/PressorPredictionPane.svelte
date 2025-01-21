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
  import ExplanationView from './ExplanationView.svelte';

  export let showGroundTruth: boolean = true;
  export let showSummary: boolean = true;
  export let collapsible: boolean = true;

  export let collapsed: boolean = collapsible;
  $: if (!collapsible) collapsed = false;

  // export let colorScale = d3.interpolateTurbo;

  type PressorPrediction = {
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

  let prediction: PressorPrediction | undefined;
  $: if (!!$patientData && !!$patientData['Vasopressor Prediction']) {
    prediction =
      $patientData['Vasopressor Prediction'].timesteps![$timestepIndex].data;
  } else {
    prediction = undefined;
  }
</script>

{#if !!prediction}
  <div class="w-full rounded-md bg-blue-50 p-4">
    <div class="flex items-center w-full gap-4">
      <div class="text-blue-700 flex-auto">
        <Fa icon={faBedPulse} class="inline mr-2" /><span
          class="font-bold uppercase font-mono mr-2">Sepsis AI Insight</span
        > Vasopressor Prediction
      </div>
      {#if showSummary}
        <div class="text-sm">
          {#if prediction.prediction_percentage > 60}High Risk{:else if prediction.prediction_percentage > 30}Moderate
            Risk{:else}Low Risk{/if},
          {#if (prediction.prediction_percentage > 60 && prediction.ground_truth == 'Yes') || (prediction.prediction_percentage < 30 && prediction.ground_truth == 'No')}
            Accurate
          {:else if (prediction.prediction_percentage < 30 && prediction.ground_truth == 'Yes') || (prediction.prediction_percentage > 60 && prediction.ground_truth == 'No')}
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
        Sepsis AI predicts a <span
          class="font-bold {prediction.prediction_percentage > 60
            ? 'text-red-600'
            : prediction.prediction_percentage > 30
              ? 'text-yellow-600'
              : 'text-green-600'}">{prediction.prediction} chance</span
        >
        that this patient will be on prolonged vasopressors over the next 24 hours{#if !!prediction.base_rate_comparison},
          {prediction.base_rate_comparison}
          compared to other patients with a similar SOFA score{/if}.
      </div>

      <ExplanationView>
        Out of 100 patients with a similar SOFA score ({prediction
          .severity_range.min} - {prediction.severity_range.max}) as this
        patient, {prediction.prediction_percentage}% were on vasopressors for at
        least 12 of the following 24 hours, compared to {prediction.base_rate_percentage}%
        of all patients with a similar SOFA score.
      </ExplanationView>
      {#if showGroundTruth && !!prediction.ground_truth}
        <div class="mt-4 text-sm text-blue-700">
          <strong>Ground Truth:</strong>
          {prediction.ground_truth}
        </div>
      {/if}
    {/if}
  </div>
{/if}
