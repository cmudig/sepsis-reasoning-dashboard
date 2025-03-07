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
  import DescriptivePane from './DescriptivePane.svelte';
  import CategoryBar from '../charts/CategoryBar.svelte';
  import Tooltip from '../utils/Tooltip.svelte';

  export let showGroundTruth: boolean = true;
  export let showSummary: boolean = true;
  export let collapsible: boolean = true;

  export let collapsed: boolean = collapsible;
  $: if (!collapsible) collapsed = false;

  export let colorSchemes = [
    d3.schemeBlues[3],
    d3.schemePurples[3],
    d3.schemeOranges[3],
  ];

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
  $: if (!!$patientData && !!$patientData['prescriptive_peer']) {
    prediction =
      $patientData['prescriptive_peer'].timesteps![$timestepIndex].data;
  } else {
    prediction = undefined;
  }

  const probabilityFormat = d3.format('.2~%');
</script>

{#if !!prediction}
  <div class="w-full rounded-md bg-blue-50 p-4">
    <div class="flex items-center w-full gap-4">
      <div class="text-blue-700 flex-auto">
        <Fa icon={faBedPulse} class="inline mr-2" /><span
          class="font-bold uppercase font-mono mr-2">Sepsis AI</span
        >
        Treatment Recommendation
        <Tooltip
          hoverTargetClass="inline text-blue-700 hover:opacity-50 px-1"
          title="This AI presents the treatments that past clinicians gave to patients similar to yours."
        />
      </div>
      {#if showSummary}
        {@const numInconsistent = prediction.prediction.reduce(
          (a, b) => a + (b.pred.consistent ? 0 : 1),
          0
        )}
        <div class="text-sm">
          {numInconsistent} inconsistent{#if !!prediction.ground_truth}, {prediction.prediction.reduce(
              (a, b, idx) =>
                a +
                (b.pred.consistent &&
                b.pred.probs.reduce(
                  (x, y) => (!x || y.prob > x.prob ? y : x),
                  null
                ).policy == prediction.ground_truth[idx].label
                  ? 1
                  : 0),
              0
            )}/{prediction.prediction.length - numInconsistent} matching true action{/if}
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
              &nbsp;most of the time{/if}.
          </div>
        </div>
        {#if !txPred.pred.consistent}
          <div class="mt-2 mb-6">
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

      {#if showGroundTruth && !!prediction.ground_truth}
        <div class="mt-4 text-sm text-blue-700">Ground truth:</div>
        {#each prediction.ground_truth as gt (gt.tx)}
          <div class="mt-2 text-sm">
            <span class="font-bold">{gt.tx}</span>: {gt.label}
          </div>
        {/each}
      {/if}
    {/if}
  </div>
{/if}
