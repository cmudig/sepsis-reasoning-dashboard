<script lang="ts">
  import Fa from 'svelte-fa';
  import type { PatientDataElement } from './patientdata';
  import { faArrowDown, faArrowUp } from '@fortawesome/free-solid-svg-icons';

  export let element: PatientDataElement;

  let valueMissing: boolean;
  $: valueMissing = !((element.present ?? true) != 0 && element.value !== null);
</script>

<div
  class="{typeof element.value === 'string' && element.value.length > 100
    ? 'py-3'
    : 'flex items-center gap-2 py-1'} mb-2 px-4 rounded-md border border-slate-200 bg-white"
  style="min-height: 4rem;"
>
  <div class="flex-auto text-sm">{element.name}</div>
  {#if valueMissing}
    <div class="shrink-0 text-right text-slate-500 text-sm">(missing)</div>
  {:else if Array.isArray(element.value)}
    <div class="text-right">
      {#each element.value as value, i (value)}
        <div class="text-sm">{value}</div>
      {/each}
    </div>
  {:else if (element.value ?? '').length > 100}
    <div class="w-full text-xs leading-relaxed">{element.value}</div>
  {:else}
    <div
      class="shrink-0 text-right"
      class:text-red-600={element.abnormal ?? false}
    >
      <div style="font-size: 1rem;">
        {#if !!element.delta && element.delta != 0}
          <Fa
            icon={element.delta > 0 ? faArrowUp : faArrowDown}
            class="inline mr-1 text-xs"
          />
        {/if}
        {element.value}
      </div>
      {#if !!element.unit}
        <div class="text-slate-500 text-xs">{element.unit}</div>
      {/if}
    </div>
  {/if}
</div>
