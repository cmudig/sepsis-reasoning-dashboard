<script lang="ts">
  import { getContext, setContext } from 'svelte';
  import {
    dataElementMatchesFilter,
    getHistoricalPatientData,
    type PatientData,
    type PatientDataElement,
    type PatientDataSection,
  } from './patientdata';
  import { writable, type Writable } from 'svelte/store';
  import DataElementGroup from './DataElementGroup.svelte';
  import DataElementView from './DataElementView.svelte';

  export let section: string | null = null;
  export let title: string | null = null;
  export let filterable: boolean = false;
  export let height: any | null = null;
  export let studyEnvironment: boolean = false;

  let patientData: Writable<PatientData> = getContext('patientData');
  let timestepIndex: Writable<number> = getContext('timestepIndex');
  let sectionData: Writable<PatientDataSection | undefined> =
    writable(undefined);
  setContext('sectionData', sectionData);

  let dataElements: PatientDataElement[] | undefined;
  $: if (!!section && !!$patientData[section]) {
    $sectionData = $patientData[section];
    if (!!$patientData[section].data) {
      dataElements = $patientData[section].data;
    } else if (!!$patientData[section].timesteps) {
      dataElements = $patientData[section].timesteps![$timestepIndex].data;
    }
  } else {
    dataElements = undefined;
  }

  export let filterText: string | null = null;
  let visibleDataElements: PatientDataElement[] | undefined;
  $: if (!!filterText && !!dataElements) {
    visibleDataElements = dataElements.filter((element) =>
      dataElementMatchesFilter(element, filterText!)
    );
  } else {
    visibleDataElements = dataElements;
  }
</script>

{#if !!dataElements && dataElements.length > 0 && !!$sectionData}
  <div
    class="w-full {!!height ? '' : 'h-full'} flex flex-col"
    style={!!height ? `height: ${height};` : ''}
  >
    <div
      class="py-2 font-bold shrink-0 text-slate-700 flex items-center gap-2 justify-between"
    >
      <div class="flex-auto shrink-0 py-1">{title ?? section}</div>
      {#if filterable}
        <input
          type="text"
          class="font-normal flat-text-input-sm w-32"
          bind:value={filterText}
          placeholder="Search"
        />
      {/if}
    </div>
    <div class="flex-auto h-0 overflow-y-auto">
      {#if !!visibleDataElements}
        {#each visibleDataElements as element, i (element.name ?? i)}
          {#if element.children}
            {#if !studyEnvironment || !(element.hide_in_study ?? false)}
              <DataElementGroup
                name={element.name}
                dataElements={element.children}
                {filterText}
                collapsed={!filterText}
                basePath={[element.name]}
                {studyEnvironment}
              />
            {/if}
          {:else}
            <DataElementView
              {element}
              historicalValues={getHistoricalPatientData(
                $sectionData,
                $timestepIndex,
                [element.name]
              )}
              {studyEnvironment}
            />
          {/if}
        {/each}
      {/if}
    </div>
  </div>
{/if}
