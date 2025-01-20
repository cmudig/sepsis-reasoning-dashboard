<script>
  import { createEventDispatcher, getContext, onMount } from 'svelte';

  const dispatch = createEventDispatcher();

  const {
    data,
    xGet,
    yGet,
    xRange,
    x,
    yRange,
    xScale,
    y,
    height,
    zGet,
    zScale,
    z,
    custom,
  } = getContext('LayerCake');

  export let textFn = (d) => d;

  export let hoveredIndex = null;

  // Disable transition until after loaded
  onMount(() => {
    setTimeout(() => (loaded = true), 100);
  });

  let loaded = false;
</script>

{#each $data as d, i}
  <span
    class="absolute pt-2 text-xs"
    class:font-bold={hoveredIndex == d.index}
    class:animated={loaded}
    style="top: 12px; left: {$xGet(d) *
      ($xRange[1] <= 1.0 ? 100 : 1)}{$xRange[1] <= 1.0
      ? '%'
      : 'px'}; width: {($xScale($z(d)) - $xGet(d)) *
      ($xRange[1] <= 1.0 ? 100 : 1)}{$xRange[1] <= 1.0 ? '%' : 'px'};"
  >
    {@html textFn(d)}
  </span>
{/each}

<style>
  .animated {
    transition-property: width, left;
    @apply duration-300 ease-in-out;
  }
</style>
