<script lang="ts">
  import { getContext, onMount } from 'svelte';
  import type { Writable } from 'svelte/store';
  import type { Explanation, PatientData } from '../patientdata';
  import Fa from 'svelte-fa';
  import {
    faBedPulse,
    faBolt,
    faChevronDown,
    faChevronRight,
    faChevronUp,
    faThumbsDown,
    faThumbsUp,
    faWarning,
  } from '@fortawesome/free-solid-svg-icons';
  import * as d3 from 'd3';
  import CategoryBar from '../charts/CategoryBar.svelte';
  import Tooltip from '../utils/Tooltip.svelte';
  import { fade } from 'svelte/transition';
  import { probabilityDescription } from '../utils/utils';

  export let shortName: string = '';
  export let longName: string = '';
  export let outcomeDescription: string = '';

  export let showGroundTruth: boolean = true;
  export let showSummary: boolean = true;
  export let collapsible: boolean = true;
  export let showExplanation: boolean = true;
  let explanationCollapsed: boolean = true;

  export let minimumSampleSize: number | undefined = undefined;
  export let warningStyle: boolean = false;
  export let rankOptions: 'best' | 'worst' = 'best';
  export let balanceFiltering: boolean = false;

  export let collapsed: boolean = collapsible;
  $: if (!collapsible) collapsed = false;

  type OutcomePrediction = {
    policy?: { tx: string; value: string }[];
    sample_size: number;
    prediction: {
      mean: number;
      std: number;
      pvalue?: number;
    };
  };
  type TreatmentOutcomePrediction = {
    average: OutcomePrediction;
    treatment_names: string[][];
    predictions: OutcomePrediction[];
    ground_truth?: string;
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

  let prediction: TreatmentOutcomePrediction | undefined;
  let sortedPredictions: OutcomePrediction[] | undefined;
  $: if (
    !!$patientData &&
    !!shortName &&
    !!$patientData[`predictive_${shortName}_dependent`]
  ) {
    prediction =
      $patientData[`predictive_${shortName}_dependent`].timesteps![
        $timestepIndex
      ].data;
  } else {
    prediction = undefined;
  }

  $: if (!!prediction) {
    sortedPredictions = [...prediction.predictions];
    if (minimumSampleSize !== undefined)
      sortedPredictions = sortedPredictions.filter(
        (p) => p.sample_size >= minimumSampleSize
      );
    else {
      // remove smaller samples past five
      sortedPredictions = sortedPredictions.sort(
        (a, b) => b.sample_size - a.sample_size
      );
      if (sortedPredictions.length > 6 && sortedPredictions[5].sample_size < 10)
        sortedPredictions = sortedPredictions.slice(0, 6);
    }
    if (rankOptions == 'worst')
      sortedPredictions.sort((a, b) => b.prediction.mean - a.prediction.mean);
    else
      sortedPredictions.sort((a, b) => a.prediction.mean - b.prediction.mean);
    if (balanceFiltering) {
      let maxLength = Math.min(
        rankOptions == 'worst'
          ? Math.floor(sortedPredictions.length / 2)
          : Math.ceil(sortedPredictions.length / 2),
        3
      );
      if (sortedPredictions.length > maxLength)
        sortedPredictions = sortedPredictions.slice(0, maxLength);
    } else if (sortedPredictions.length > 3)
      sortedPredictions = sortedPredictions.slice(0, 3);
  } else {
    sortedPredictions = undefined;
  }

  const probabilityFormat = d3.format('.0~%');

  const replacePhrases: { [key: string]: string } = {
    '100 mL to 1 L': 'up to 1 L',
    '< 100 mL of': 'no',
  };

  const numberStrings = [
    'no treatment plans',
    'one treatment plan',
    'two treatment plans',
    'three treatment plans',
  ];

  function getPolicyLabel(
    policyType: 'Volume' | 'Vasopressors',
    policyValue: string
  ) {
    let idx = TreatmentPolicyNames[policyType].indexOf(policyValue);
    let result: string = policyValue;
    if (idx >= 0)
      result =
        prediction?.treatment_names[policyType == 'Volume' ? 0 : 1][idx] ??
        policyValue;
    Object.entries(replacePhrases).forEach(
      ([pat, repl]) => (result = result.replaceAll(pat, repl))
    );
    return result;
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
            {#if warningStyle}
              Sepsis AI found {numberStrings[sortedPredictions.length]} you may want
              to avoid. Compared to other plans taken for similar patients, {sortedPredictions.length !=
              1
                ? 'these plans were'
                : 'this plan was'} associated with
              <span class="text-rose-800 font-semibold"
                >higher risk of mortality in this admission</span
              > if given over the next four hours.
            {:else}
              Sepsis AI found {numberStrings[sortedPredictions.length]} you may want
              to consider. Compared to other plans taken for similar patients, {sortedPredictions.length !=
              1
                ? 'these plans were'
                : 'this plan was'} associated with
              <span class="text-blue-800 font-semibold"
                >lower risk of mortality in this admission</span
              > if given over the next four hours.
            {/if}
          </div>
        {/if}
        <div class="mt-4 space-y-2">
          {#each sortedPredictions as pred, i (i)}
            {#if visible}
              <div
                class="rounded-md bg-gray-100 border-2 border-gray-300 p-4 w-full flex flex-wrap justify-stretch items-center gap-4"
                in:fade={{ delay: i * 200 }}
              >
                {#if warningStyle}
                  <div class="text-gray-400/50 text-xl">
                    <Fa icon={faThumbsDown} />
                  </div>
                {:else}
                  <div class="text-gray-400/50 text-xl">
                    <Fa icon={faThumbsUp} />
                  </div>
                {/if}
                <div class="flex-auto w-0">
                  <div class="mb-1">
                    <strong
                      >{getPolicyLabel(
                        'Volume',
                        pred.policy?.[0].value ?? 'unknown'
                      )}</strong
                    >
                    and
                    <strong
                      >{getPolicyLabel(
                        'Vasopressors',
                        pred.policy?.[1].value ?? 'unknown'
                      )}</strong
                    >
                  </div>
                  <div class="text-sm text-gray-700">
                    <span class="font-semibold"
                      >{probabilityDescription(
                        pred.prediction.mean,
                        prediction?.average.prediction.mean ?? 0.5
                      )}</span
                    >
                    risk of mortality (compared to other treatments)
                  </div>
                </div>
              </div>
            {/if}
          {/each}
        </div>
        {#if showGroundTruth && !!prediction.ground_truth}
          <div class="mt-4 text-sm text-blue-700">
            Ground truth: <strong>{prediction.ground_truth}</strong>
          </div>
        {/if}
        {#if visible}
          <div class="mt-4 text-sm measure">
            This prediction is based on treatment plans and mortality outcomes
            for 100 patients that Sepsis AI considers similar to this one in
            presentation, current status, and overall disease severity.
          </div>
        {/if}
      {/if}
    </div>
  </div>
{/if}
