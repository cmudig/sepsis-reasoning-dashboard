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
  import CategoryBar from '../charts/CategoryBar.svelte';
  import Tooltip from '../utils/Tooltip.svelte';

  export let shortName: string = '';
  export let longName: string = '';
  export let outcomeDescription: string = '';

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
    sortedPredictions.sort((a, b) => a.prediction.mean - b.prediction.mean);
  } else {
    sortedPredictions = undefined;
  }

  const probabilityFormat = d3.format('.0~%');

  // https://pmc.ncbi.nlm.nih.gov/articles/PMC11067312/
  function riskDescription(mean: number): string {
    if (mean <= 0.05) return 'extremely unlikely';
    else if (mean <= 0.15) return 'very unlikely';
    else if (mean <= 0.3) return 'unlikely';
    else if (mean <= 0.6) return 'possible';
    else if (mean <= 0.8) return 'likely';
    else if (mean <= 0.99) return 'very likely';
    else return 'extremely likely';
  }

  const replacePhrases: { [key: string]: string } = {
    '100 mL to 1 L': 'up to 1 L',
    '< 100 mL of': 'no',
  };

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
</script>

{#if !!prediction && !!sortedPredictions}
  <div class="w-full rounded-md bg-blue-50 p-4">
    <div class="flex items-center w-full gap-4">
      <div class="text-blue-700 flex-auto">
        <Fa icon={faBedPulse} class="inline mr-2" /><span
          class="font-bold uppercase font-mono mr-2">Sepsis AI</span
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
      <div class="mt-2 measure">
        Sepsis AI identified the following viable treatment plans for this
        patient over the next four hours:
      </div>
      <div class="mt-2 space-y-2">
        {#each sortedPredictions as pred, i (i)}
          <div
            class="rounded-md bg-blue-100 p-4 w-full flex flex-wrap justify-stretch gap-4"
          >
            <div class="flex-auto w-0" style="min-width: 180px;">
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
            <div class="flex-auto w-0" style="min-width: 180px;">
              <Tooltip title="{probabilityFormat(pred.prediction.mean)} chance"
                ><span
                  class="font-bold hoverable-text {pred.prediction.mean > 0.6
                    ? 'text-red-600'
                    : pred.prediction.mean > 0.3
                      ? 'text-yellow-600'
                      : 'text-green-600'}"
                  >{riskDescription(pred.prediction.mean)}</span
                ></Tooltip
              > to {outcomeDescription},
              {#if (pred.prediction.pvalue ?? 0) > 0.05}
                about the same as
              {:else if pred.prediction.mean > (prediction.average.prediction.mean ?? 0)}
                <strong>significantly worse</strong> than
              {:else}
                <strong>significantly better</strong> than
              {/if}
              <Tooltip
                title="{probabilityFormat(
                  prediction.average.prediction.mean
                )} chance on average"
                ><span class="hoverable-text">other treatments</span></Tooltip
              >
            </div>
          </div>
        {/each}
      </div>
      {#if showGroundTruth && !!prediction.ground_truth}
        <div class="mt-4 text-sm text-blue-700">
          Ground truth: <strong>{prediction.ground_truth}</strong>
        </div>
      {/if}
      <div class="mt-2 text-sm measure">
        This prediction is based on mortality outcomes for 100 patients that
        Sepsis AI considers similar to this one in presentation and disease
        severity.
      </div>
    {/if}
  </div>
{/if}
