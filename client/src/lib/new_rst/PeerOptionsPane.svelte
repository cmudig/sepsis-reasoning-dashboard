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

  export let showGroundTruth: boolean = true;
  export let collapsible: boolean = true;

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
    sortedPredictions.sort((a, b) => b.sample_size - a.sample_size);
  } else {
    sortedPredictions = undefined;
  }

  const probabilityFormat = d3.format('.0~%');

  // https://pmc.ncbi.nlm.nih.gov/articles/PMC11067312/
  function frequencyDescription(frequency: number): string {
    frequency = frequency / 100;
    if (frequency <= 0.05) return 'almost never';
    else if (frequency <= 0.15) return 'rarely';
    else if (frequency <= 0.3) return 'infrequently';
    else if (frequency <= 0.6) return 'often';
    else if (frequency <= 0.8) return 'frequently';
    else if (frequency <= 0.99) return 'very frequently';
    else return 'almost always';
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
              <Tooltip title="{pred.sample_size}/100 similar patients"
                ><span
                  class="font-bold hoverable-text {pred.sample_size > 30
                    ? 'text-green-600'
                    : pred.sample_size >= 15
                      ? 'text-yellow-600'
                      : 'text-red-600'}"
                  >{frequencyDescription(pred.sample_size)}</span
                ></Tooltip
              >
              prescribed for similar patients
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
        This prediction is based on prior clinicians' treatment decisions for
        100 patients that Sepsis AI considers similar to this one in
        presentation and disease severity.
      </div>
    {/if}
  </div>
{/if}
