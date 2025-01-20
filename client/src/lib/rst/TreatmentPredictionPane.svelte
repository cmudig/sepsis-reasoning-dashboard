<script lang="ts">
  import { getContext } from 'svelte';
  import type { Writable } from 'svelte/store';
  import type { PatientData } from '../patientdata';
  import Fa from 'svelte-fa';
  import {
    faBedPulse,
    faChevronDown,
    faChevronRight,
  } from '@fortawesome/free-solid-svg-icons';
  import * as d3 from 'd3';
  import ExplanationView from './ExplanationView.svelte';
  import CategoryBar from '../charts/CategoryBar.svelte';

  export let showGroundTruth: boolean = true;

  export let colorSchemes = [
    d3.schemeBlues[3],
    d3.schemePurples[3],
    d3.schemeOranges[3],
  ];

  $: console.log(colorSchemes[2]);

  type TreatmentPrediction = {
    prediction: {
      tx: string;
      pred: {
        probs: { policy: string; prob: number }[];
        choice: string;
        choice_prob?: number;
        consistent: boolean;
      };
    }[];
    ground_truth?: {
      tx: string;
      label: string;
    }[];
    severity_range: {
      min: number;
      max: number;
    };
  };

  let patientData: Writable<PatientData> = getContext('patientData');
  let timestepIndex: Writable<number> = getContext('timestepIndex');

  let prediction: TreatmentPrediction | undefined;
  $: if (!!$patientData && !!$patientData['Treatment Prediction']) {
    prediction =
      $patientData['Treatment Prediction'].timesteps![$timestepIndex].data;
  } else {
    prediction = undefined;
  }

  const probabilityFormat = d3.format('.2~%');
</script>

{#if !!prediction}
  <div class="w-full rounded-md bg-blue-50 p-4">
    <div class="pb-2 text-blue-700">
      <Fa icon={faBedPulse} class="inline mr-2" /><span
        class="font-bold uppercase font-mono mr-2">Sepsis AI Insight</span
      > Treatment Prediction
    </div>
    {#each prediction.prediction as txPred, i (txPred.tx)}
      <div class="mt-4 flex items-baseline gap-4">
        <div
          class="font-bold text-sm uppercase shrink-0"
          style="color: {colorSchemes[i][colorSchemes[i].length - 1]};"
        >
          {txPred.tx}
        </div>
        <div class="measure">
          Clinicians would <span class="font-bold">{txPred.pred.choice}</span>
          for similar patients over the next 4 hours{#if !!txPred.pred.choice_prob}
            &nbsp;({probabilityFormat(txPred.pred.choice_prob)} of the time){/if}.
        </div>
      </div>
      {#if !txPred.pred.consistent}
        <div class="mt-2 mb-5">
          <CategoryBar
            width={null}
            counts={Object.fromEntries(
              txPred.pred.probs.map((p) => [p.policy, p.prob])
            )}
            order={txPred.pred.probs.map((p) => p.policy)}
            colorScale={colorSchemes[i]}
          />
        </div>
      {/if}
    {/each}

    <ExplanationView>
      The recommendation shows the frequency of treatment actions over 100
      patients with a similar SOFA score ({prediction.severity_range.min} - {prediction
        .severity_range.max}) as this patient.
    </ExplanationView>
    {#if showGroundTruth && !!prediction.ground_truth}
      <div class="mt-4 text-sm text-blue-700">Ground truth:</div>
      {#each prediction.ground_truth as gt (gt.tx)}
        <div class="mt-2 text-sm">
          <span class="font-bold">{gt.tx}</span>: {gt.label}
        </div>
      {/each}
    {/if}
  </div>
{/if}
