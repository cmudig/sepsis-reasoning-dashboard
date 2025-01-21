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

  type OutcomePrediction = {
    policy?: { tx: string; value: number }[];
    sample_size: number;
    predictions: {
      target: string;
      mean: number;
      std: number;
      pvalue?: number;
    }[];
  };
  type TreatmentOutcomePrediction = {
    average: OutcomePrediction;
    predictions: OutcomePrediction[];
    ground_truth?: {
      target: string;
      label: string;
    }[];
    severity_range: {
      min: number;
      max: number;
    };
  };

  const TreatmentPolicyNames: { [key: string]: string[] } = {
    'IV Fluids': ['Conservative', 'Moderate', 'Aggressive'],
    Vasopressors: ['None', 'Low-Dose', 'High-Dose'],
    Diuretics: ['No', 'Yes'],
  };

  let patientData: Writable<PatientData> = getContext('patientData');
  let timestepIndex: Writable<number> = getContext('timestepIndex');

  let visibleTarget: string = 'Mortality';

  let prediction: TreatmentOutcomePrediction | undefined;
  let selectedPolicy: number[] = [0, 0, 0];
  let policyPrediction: OutcomePrediction | null = null;
  $: if (!!$patientData && !!$patientData['Treatment Outcome Prediction']) {
    prediction =
      $patientData['Treatment Outcome Prediction'].timesteps![$timestepIndex]
        .data;
    if (!!prediction) {
      let maxPolicy = (
        prediction.predictions.reduce(
          (prev, curr) => (curr.sample_size > prev.sample_size ? curr : prev),
          { sample_size: 0 }
        ) as OutcomePrediction
      ).policy;
      if (!!maxPolicy) selectedPolicy = maxPolicy.map((p) => p.value);
      else selectedPolicy = [0, 0, 0];
    }
  } else {
    prediction = undefined;
  }

  $: if (!!prediction) {
    policyPrediction =
      prediction.predictions.find((p) =>
        p.policy?.every((x, i) => x.value == selectedPolicy[i])
      ) ?? null;
  } else {
    policyPrediction = null;
  }

  const probabilityFormat = d3.format('.2~%');
</script>

{#if !!prediction}
  <div class="w-full rounded-md bg-blue-50 p-4">
    <div class="pb-2 text-blue-700">
      <Fa icon={faBedPulse} class="inline mr-2" /><span
        class="font-bold uppercase font-mono mr-2">Sepsis AI Insight</span
      > Outcome Prediction
    </div>
    <div class="flex gap-4 w-full items-start">
      <div
        class="rounded-md bg-blue-100 p-4 flex flex-col gap-4"
        style="min-width: 300px; max-width: 50%;"
      >
        <div class="text-sm">
          Select a treatment policy for the next 4 hours to see how the
          patient's outcome risk may change:
        </div>
        {#each ['IV Fluids', 'Vasopressors', 'Diuretics'] as tx, i}
          <div class="w-full">
            <div
              class="font-bold text-sm uppercase"
              style="color: {colorSchemes[i][colorSchemes[i].length - 1]};"
            >
              {tx}
            </div>
            <div class="mt-1 flex items-stretch gap-2 w-full">
              {#each TreatmentPolicyNames[tx] as policyVal, policyIdx}
                <button
                  class="rounded-md py-2 px-4 grow shrink basis-1 text-xs {selectedPolicy[
                    i
                  ] == policyIdx
                    ? 'text-white font-bold'
                    : 'bg-blue-50 hover:bg-blue-200'}"
                  class:opacity-30={!prediction.predictions.find((p) =>
                    p.policy?.every(
                      (x, j) =>
                        x.value == (j == i ? policyIdx : selectedPolicy[j])
                    )
                  )}
                  style={selectedPolicy[i] == policyIdx
                    ? `background-color: ${colorSchemes[i][colorSchemes[i].length - 1]};`
                    : ''}
                  disabled={selectedPolicy[i] == policyIdx}
                  on:click={() =>
                    (selectedPolicy = [
                      ...selectedPolicy.slice(0, i),
                      policyIdx,
                      ...selectedPolicy.slice(i + 1),
                    ])}>{policyVal}</button
                >
              {/each}
            </div>
          </div>
        {/each}
      </div>
      <div class="flex-auto basis-0">
        <div class="measure">
          {#if !!policyPrediction}
            <strong>{policyPrediction.sample_size}</strong> out of {prediction
              .average.sample_size} similar patients received the selected treatment
            policy.
          {:else}
            <span class="text-slate-600"
              >Predictions cannot be shown for this treatment policy because not
              enough similar patients received it.</span
            >
          {/if}
        </div>
        {#if !!policyPrediction}
          {@const targetPrediction = policyPrediction.predictions.find(
            (p) => p.target == visibleTarget
          )}
          <div class="w-full flex gap-3">
            {#each policyPrediction.predictions as predTarget (predTarget.target)}
              <button
                class="flex-auto basis-1 rounded my-2 py-1 text-sm text-center {visibleTarget ==
                predTarget.target
                  ? 'bg-slate-600 text-white font-bold hover:bg-slate-700'
                  : 'text-slate-700 hover:bg-slate-300'}"
                on:click={() => (visibleTarget = predTarget.target)}
                >{predTarget.target}</button
              >
            {/each}
          </div>
          {#if !!targetPrediction}
            <div class="measure">
              The risk of {visibleTarget}
              <strong
                >{targetPrediction.mean > 0 ? 'increases' : 'decreases'} by {probabilityFormat(
                  Math.abs(targetPrediction.mean)
                )}</strong
              >
              after 4 hours,
              {#if (targetPrediction?.pvalue ?? 0) > 0.05}
                about the same as other similar patients.
              {:else if targetPrediction.mean > (prediction.average.predictions.find((p) => p.target == visibleTarget)?.mean ?? 0)}
                <strong>significantly worse</strong> than other similar patients.
              {:else}
                <strong>significantly better</strong> than other similar patients.
              {/if}
            </div>
          {/if}
        {/if}
      </div>
    </div>
    <!-- {#each prediction.prediction as txPred, i (txPred.tx)}
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
    {/each} -->

    <ExplanationView>
      The recommendation shows changes in outcome risk over {prediction.average
        .sample_size} patients with a similar SOFA score ({prediction
        .severity_range.min} - {prediction.severity_range.max}) as this patient.
    </ExplanationView>
    {#if showGroundTruth && !!prediction.ground_truth}
      <div class="mt-4 text-sm text-blue-700">Ground truth:</div>
      {#each prediction.ground_truth as gt (gt.target)}
        <div class="mt-2 text-sm">
          <span class="font-bold">{gt.target}</span>: {gt.label}
        </div>
      {/each}
    {/if}
  </div>
{/if}
