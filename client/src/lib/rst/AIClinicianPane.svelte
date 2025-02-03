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
</script>

{#if !!recommendation}
  <div class="w-full rounded-md bg-blue-50 p-4">
    <div class="flex items-center w-full gap-4">
      <div class="text-blue-700 flex-auto">
        <Fa icon={faBedPulse} class="inline mr-2" /><span
          class="font-bold uppercase font-mono mr-2">Sepsis AI Insight</span
        > Treatment Recommendation
      </div>
      {#if showSummary && !!recommendation.ground_truth}
        <div class="text-sm">
          {recommendation.recommendation.reduce(
            (a, b, i) =>
              a + (b.value == recommendation.ground_truth[i].label ? 1 : 0),
            0
          )} matching true action
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
        Over the next 4 hours, Sepsis AI recommends that you
        {#each recommendation.recommendation.slice(0, recommendation.recommendation.length - 1) as rec (rec.tx)}
          <strong>{rec.description}</strong>
        {/each}and
        <strong
          >{recommendation.recommendation[
            recommendation.recommendation.length - 1
          ].description}</strong
        >. This recommendation is based on treatments for similar patients that
        led to the lowest risk of mortality.
      </div>
      {#if showGroundTruth && !!recommendation.ground_truth}
        <div class="mt-4 text-sm text-blue-700">Ground truth:</div>
        {#each recommendation.ground_truth as gt, i (gt.tx)}
          <div class="mt-2 text-sm">
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
{/if}
