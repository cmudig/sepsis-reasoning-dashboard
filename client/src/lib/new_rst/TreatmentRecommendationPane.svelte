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
    faThumbsUp,
  } from '@fortawesome/free-solid-svg-icons';
  import * as d3 from 'd3';
  import { fade } from 'svelte/transition';
  import { probabilityDescription } from '../utils/utils';

  export let showGroundTruth: boolean = true;
  export let showSummary: boolean = true;
  export let collapsible: boolean = true;
  export let showExplanation: boolean = true;
  let explanationCollapsed: boolean = true;

  export let collapsed: boolean = collapsible;
  $: if (!collapsible) collapsed = false;

  export let colorSchemes = [
    d3.schemeBlues[3],
    d3.schemePurples[3],
    d3.schemeOranges[3],
  ];

  type Recommendation = {
    recommendation: { tx: string; value: string; description: string }[];
    sample_size: number;
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

  type TreatmentOutcomePrediction = {
    average: any;
    predictions: any[];
  };

  let patientData: Writable<PatientData> = getContext('patientData');
  let timestepIndex: Writable<number> = getContext('timestepIndex');

  let recommendation: Recommendation | undefined;
  $: if (!!$patientData && !!$patientData['prescriptive_outcome']) {
    recommendation =
      $patientData['prescriptive_outcome'].timesteps![$timestepIndex].data;
  } else {
    recommendation = undefined;
  }

  let outcomePredictions: TreatmentOutcomePrediction | undefined;
  $: if (!!$patientData && !!$patientData[`predictive_morta_dependent`]) {
    outcomePredictions =
      $patientData[`predictive_morta_dependent`].timesteps![$timestepIndex]
        .data;
    console.log(outcomePredictions);
  } else {
    outcomePredictions = undefined;
  }

  let visible = false;
  onMount(() => {
    visible = true;
  });
</script>

{#if !!recommendation}
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
      {#if !collapsed && visible}
        <div class="mt-2 measure" in:fade>
          Sepsis AI identified a treatment plan you may want to consider.
          Compared to other plans taken for similar patients, this plan was
          associated with the
          <span class="text-blue-800 font-semibold"
            >lowest risk of mortality in this admission</span
          > if given over the next four hours.
        </div>
        <div
          class="mt-4 rounded-md bg-gray-100 border-2 border-gray-300 p-4 w-full flex flex-wrap justify-stretch items-center gap-4"
          in:fade={{ delay: 200 }}
        >
          <div class="text-gray-400/50 text-xl">
            <Fa icon={faThumbsUp} />
          </div>
          <div class="flex-auto w-0">
            <div class="mb-1">
              <strong>{recommendation.recommendation[0].description}</strong>
              and
              <strong
                >{recommendation.recommendation[
                  recommendation.recommendation.length - 1
                ].description}</strong
              >
            </div>
            {#if !!outcomePredictions}
              {@const matchingPred = outcomePredictions.predictions.find((p) =>
                p.policy.every(
                  (pol, i) =>
                    pol.value == recommendation?.recommendation[i].value
                )
              )}
              {#if !!matchingPred}
                <div class="text-sm text-gray-700">
                  <span class="font-semibold"
                    >{probabilityDescription(
                      matchingPred.prediction.mean,
                      outcomePredictions?.average.prediction.mean ?? 0.5
                    )}</span
                  >
                  risk of mortality (compared to other treatments)
                </div>
              {/if}
            {/if}
          </div>
        </div>
        <div class="mt-4 text-sm measure" in:fade>
          This recommendation is based on mortality outcomes for 100 patients
          that Sepsis AI considers similar to this one in presentation, current
          status, and overall disease severity.
        </div>
        {#if showGroundTruth && !!recommendation.ground_truth}
          <div class="mt-4 text-sm text-blue-700">Ground truth:</div>
          {#each recommendation.ground_truth as gt, i (gt.tx)}
            <div class="mt-4 text-sm">
              <span
                class="font-bold"
                style="color: {colorSchemes[i][colorSchemes[i].length - 1]};"
                >{gt.tx}</span
              >: {gt.label}
            </div>
          {/each}
        {/if}
      {/if}
    </div>
  </div>
{/if}
