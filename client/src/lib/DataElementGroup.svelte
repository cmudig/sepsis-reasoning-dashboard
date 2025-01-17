<script lang="ts">
  import Fa from 'svelte-fa';
  import DataElementView from './DataElementView.svelte';
  import {
    dataElementMatchesFilter,
    type PatientDataElement,
  } from './patientdata';
  import {
    faChevronDown,
    faChevronRight,
  } from '@fortawesome/free-solid-svg-icons';

  export let name: string;
  export let dataElements: PatientDataElement[] = [];
  export let indent = 0;

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

  let collapsed = false;
</script>

{#if visibleDataElements.length > 0}
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
        class="inline mr-2"
        icon={collapsed ? faChevronRight : faChevronDown}
      />{name}
    </button>
    {#if !collapsed}
      {#each visibleDataElements as element, i (element.name ?? i)}
        {#if element.children}
          <svelte:self
            name={element.name}
            dataElements={element.children}
            indent={indent + 1}
            {filterText}
          />
        {:else}
          <DataElementView {element} />
        {/if}
      {/each}
    {/if}
  </div>
{/if}
