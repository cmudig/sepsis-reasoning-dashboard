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

  export let colorScale = d3.interpolateTurbo;

  type Explanation = {
    feature: string;
    value: string;
    base_rate: string;
    group_rate: string;
  };

  export let showSummary: boolean = true;
  export let collapsible: boolean = true;

  export let collapsed: boolean = collapsible;
  $: if (!collapsible) collapsed = false;

  let patientData: Writable<PatientData> = getContext('patientData');
  let timestepIndex: Writable<number> = getContext('timestepIndex');

  let explanation: { similar: Explanation[]; different: Explanation[] } | null =
    null;
  $: if (!!$patientData && !!$patientData['descriptive']) {
    explanation = $patientData['descriptive'].timesteps![$timestepIndex].data;
  } else {
    explanation = null;
  }
</script>

{#if !!explanation}
  <div class="w-full rounded-md bg-blue-50 p-4">
    <div class="flex items-center w-full gap-4">
      <div class="text-blue-700 flex-auto">
        <Fa icon={faBedPulse} class="inline mr-2" /><span
          class="font-bold uppercase font-mono mr-2">Sepsis AI Insight</span
        > Similar and Different Patient Features
      </div>
      {#if showSummary}
        <div class="text-sm">
          {explanation.similar.length} similar, {explanation.different.length} different
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
        Sepsis AI found that this patient is <strong>similar</strong> to a cohort
        of other patients that often share these features:
      </div>

      <div class="flex items-stretch gap-4 mt-4">
        {#each explanation.similar as expFeature}
          <div
            class="rounded bg-blue-100 p-4 flex-auto basis-1 text-center text-sm"
          >
            <div class="font-bold">{expFeature.feature}</div>
            <div>{expFeature.value}</div>
          </div>
        {/each}
      </div>

      <div class="mt-2 measure">
        Meanwhile, this patient could be <strong>unusual</strong> because of the
        following features:
      </div>

      <div class="flex items-stretch gap-4 mt-4">
        {#each explanation.different as expFeature}
          <div
            class="rounded bg-blue-100 p-4 flex-auto basis-1 text-center text-sm"
          >
            <div class="font-bold">{expFeature.feature}</div>
            <div>{expFeature.value}</div>
          </div>
        {/each}
      </div>
    {/if}
  </div>
{/if}
