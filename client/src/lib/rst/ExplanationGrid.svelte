<script lang="ts">
  import type { Explanation } from '../patientdata';

  export let explanation: Explanation[] | null = null;
</script>

{#if !!explanation}
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
