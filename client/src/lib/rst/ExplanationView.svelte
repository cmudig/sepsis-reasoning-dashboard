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

  export let showGroundTruth: boolean = true;

  export let colorScale = d3.interpolateTurbo;

  type Explanation = {
    feature: string;
    value: string;
    base_rate: string;
    group_rate: string;
  };

  let patientData: Writable<PatientData> = getContext('patientData');
  let timestepIndex: Writable<number> = getContext('timestepIndex');

  let explanationCollapsed: boolean = true;

  let explanation: Explanation[] | null = null;
  $: if (!!$patientData && !!$patientData['Explanation']) {
    explanation = $patientData['Explanation'].timesteps![$timestepIndex].data;
  } else {
    explanation = null;
  }
</script>

<div class="rounded-md border border-blue-200 p-4 my-4 bg-white">
  <button
    class="flex items-center w-full gap-2 text-left hover:opacity-50"
    on:click={() => (explanationCollapsed = !explanationCollapsed)}
  >
    <Fa
      icon={explanationCollapsed ? faChevronRight : faChevronDown}
      class="text-sm"
    />
    <div class="italic">Why did Sepsis AI make this prediction?</div>
  </button>
  {#if !explanationCollapsed}
    <div class="mt-4 text-sm measure">
      <slot />
    </div>
    {#if !!explanation}
      <div class="mt-4 text-sm measure">
        The 100 most similar patients to this one tend to have the following
        characteristics:
      </div>
      <div class="flex items-stretch gap-4 mt-4">
        {#each explanation as expFeature}
          <div
            class="rounded bg-blue-100 p-4 flex-auto basis-1 text-center text-sm"
          >
            <div class="font-bold">{expFeature.feature}</div>
            <div>{expFeature.value}</div>
          </div>
        {/each}
      </div>
    {/if}
  {/if}
</div>
