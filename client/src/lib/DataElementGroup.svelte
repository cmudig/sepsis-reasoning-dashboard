<svelte:options accessors />

<script lang="ts">
  import Fa from 'svelte-fa';
  import DataElementView from './DataElementView.svelte';
  import {
    dataElementMatchesFilter,
    getHistoricalPatientData,
    type PatientData,
    type PatientDataElement,
    type PatientDataSection,
  } from './patientdata';
  import {
    faChevronDown,
    faChevronRight,
  } from '@fortawesome/free-solid-svg-icons';
  import type { Writable } from 'svelte/store';
  import { getContext } from 'svelte';

  let sectionData: Writable<PatientDataSection | undefined> =
    getContext('sectionData');
  let timestepIndex: Writable<number> = getContext('timestepIndex');

  export let name: string;
  export let dataElements: PatientDataElement[] = [];
  export let indent = 0;
  export let basePath: string[] = [];
  export let studyEnvironment: boolean = false;

  export let filterText: string | null = null;
  let visibleDataElements: PatientDataElement[] = [];
  $: if (!!filterText) {
    if (name.toLocaleLowerCase().includes(filterText.toLocaleLowerCase())) {
      visibleDataElements = dataElements;
    } else {
      visibleDataElements = dataElements.filter((element) =>
        dataElementMatchesFilter(element, filterText)
      );
    }
  } else {
    visibleDataElements = dataElements;
  }

  export let collapsed = false;

  export function expand() {
    collapsed = false;
  }
</script>

{#if visibleDataElements.length > 0 && !!$sectionData}
  <div
    class="bg-slate-100 rounded-md mb-2"
    style="padding-left: {indent +
      0.5}rem; padding-right: 0.5rem; padding-bottom: 0.05px;"
  >
    <button
      on:click={() => (collapsed = !collapsed)}
      class="hover:opacity-50 text-sm font-bold text-slate-700 py-2 px-2 text-left w-full"
    >
      <Fa
        class="inline mr-2 {!collapsed ? 'rotate-90' : ''}"
        icon={faChevronRight}
      />{name}
    </button>
    {#if !collapsed}
      {#each visibleDataElements as element, i (element.name ?? i)}
        {#if element.children}
          {#if !studyEnvironment || !(element.hide_in_study ?? false)}
            <svelte:self
              name={element.name}
              dataElements={element.children}
              indent={indent + 1}
              {filterText}
              collapsed={!filterText}
              basePath={[...basePath, element.name]}
              {studyEnvironment}
            />
          {/if}
        {:else}
          <DataElementView
            {element}
            historicalValues={getHistoricalPatientData(
              $sectionData,
              $timestepIndex,
              [...basePath, element.name]
            )}
            {studyEnvironment}
          />
        {/if}
      {/each}
    {/if}
  </div>
{/if}
