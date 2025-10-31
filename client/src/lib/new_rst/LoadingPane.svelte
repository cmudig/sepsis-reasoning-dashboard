<script lang="ts">
  import { faBedPulse } from '@fortawesome/free-solid-svg-icons';
  import Fa from 'svelte-fa';

  export let showInset: boolean = false;
</script>

<div
  class="w-full rounded-[8px] p-0.5 bg-gradient-to-br from-blue-600 via-purple-500 to-rose-500 loading-border relative"
>
  <div class="w-full rounded-md bg-gray-50 p-4">
    <div class="flex items-center w-full gap-4">
      <div class="text-blue-600 flex-auto">
        <Fa icon={faBedPulse} class="inline mr-2" /><span
          class="inline-block font-bold bg-clip-text text-transparent bg-gradient-to-br from-blue-600 via-purple-500 to-rose-500 font-bold uppercase font-mono mr-2"
          >Sepsis AI</span
        >
      </div>
    </div>
    <div class="mt-2 w-full loading-placeholder"></div>
    {#if showInset}
      <div
        class="mt-4 rounded-md bg-gray-100 border-2 border-gray-300 p-4 w-full flex flex-wrap justify-stretch gap-4"
      >
        <div
          class="flex-auto w-0 loading-placeholder"
          style="min-width: 180px;"
        ></div>
        <div
          class="flex-auto w-0 loading-placeholder"
          style="min-width: 180px;"
        ></div>
      </div>
    {/if}
    <div class="mt-4 text-sm loading-placeholder"></div>
  </div>
</div>

<style>
  .loading-placeholder {
    @apply bg-gray-200 rounded-md animate-pulse h-6 w-full;
  }

  .loading-border::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    opacity: 0;
    background-color: white;
    animation: pulse 4s cubic-bezier(0.4, 0, 0.6, 1) infinite;
  }
</style>
