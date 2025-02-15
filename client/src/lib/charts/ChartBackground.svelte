<!--
  @component
  Generates an SVG x-axis. This component is also configured to detect if your x-scale is an ordinal scale. If so, it will place the markers in the middle of the bandwidth.
 -->
<script>
  import { getContext } from 'svelte';
  const { width, height, yRange, xRange } = getContext('LayerCake');

  export let inset = 0;
</script>

<div
  class="absolute {$$props.class ?? ''}"
  style="top: {Math.min(...$yRange) + inset}px; left: {$xRange[0] +
    inset}px; width: {$xRange[1] - $xRange[0] - inset * 2}px; height: {Math.abs(
    $yRange[1] - $yRange[0]
  ) -
    inset * 2}px;"
></div>
