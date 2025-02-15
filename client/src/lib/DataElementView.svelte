<script lang="ts">
  import Fa from 'svelte-fa';
  import type { PatientDataElement } from './patientdata';
  import {
    faArrowDown,
    faArrowUp,
    faCheckCircle,
    faXmarkCircle,
  } from '@fortawesome/free-solid-svg-icons';
  import { Html, LayerCake, Svg } from 'layercake';
  import ShadingX from './charts/ShadingX.svelte';
  import AxisX from './charts/AxisX.svelte';
  import AxisY from './charts/AxisY.svelte';
  import Line from './charts/Line.svelte';
  import Tooltip from './utils/Tooltip.svelte';
  import * as d3 from 'd3';
  import ChartTooltip from './charts/ChartTooltip.svelte';
  import ChartBackground from './charts/ChartBackground.svelte';

  export let element: PatientDataElement;
  export let historicalValues: {
    time: number;
    data: PatientDataElement | null;
  }[] = [];

  let valueMissing: boolean;
  $: valueMissing = !((element.present ?? true) != 0 && element.value !== null);

  let expanded: boolean = false;

  let pastData: {
    i: number;
    x: number;
    y: number | null;
    rawValue: string | null;
  }[] = [];
  let dataBoolean: boolean = false;

  $: if (historicalValues.length > 0) {
    let dataNumeric = historicalValues.every(
      (v) => !Number.isNaN(parseFloat((v.data?.value ?? '0') as string))
    );
    console.log(historicalValues);
    dataBoolean = historicalValues.every(
      (v) =>
        typeof (v.data?.value ?? 'No') === 'string' &&
        ['yes', 'no', 'true', 'false', 'previously'].includes(
          ((v.data?.value ?? 'No') as string).toLocaleLowerCase()
        )
    );
    if (dataNumeric || dataBoolean)
      pastData = historicalValues.map((v, i) => ({
        i,
        x: v.time,
        y:
          !!v.data && (v.data.present ?? true)
            ? dataBoolean
              ? ['yes', 'true'].includes(
                  ((v.data?.value ?? 'No') as string).toLocaleLowerCase()
                )
                ? 1
                : 0
              : parseFloat((v.data?.value ?? '0') as string)
            : null,
        rawValue: (v.data?.value ?? null) as string | null,
      }));
    else pastData = [];
  }

  function formatTimeDelta(timestamp: number, short = false) {
    // calculate how far away dataIndex is from the end of the list of historical values
    let hours = Math.round(
      (pastData[pastData.length - 1].x - timestamp) / 3600
    );
    if (short) {
      if (hours == 0) return 'now';
      if (hours % 24 == 0) return `${hours / 24}d`;
      return `${hours}h`;
    }
    return hours == 0 ? 'Just now' : hours + ' hours ago';
  }

  function createXTicks(data: { x: number; y: number | null }[]): number[] {
    if (data.every((d) => d.y === null || d.y === undefined)) return [];
    let minTime = data[0].x;
    let maxTime = data[data.length - 1].x;
    if (maxTime - minTime <= 24 * 3600) {
      // tick every interval
      return data.map((d) => d.x);
    } else if (maxTime - minTime <= 2 * 24 * 3600) {
      // every 12 h
      return data
        .map((d) => d.x)
        .filter(
          (x, i) =>
            Math.round((maxTime - x) / (12 * 3600)) ==
            (maxTime - x) / (12 * 3600)
        );
    } else {
      // every day
      return data
        .map((d) => d.x)
        .filter(
          (x, i) =>
            Math.round((maxTime - x) / (24 * 3600)) ==
            (maxTime - x) / (24 * 3600)
        );
    }
  }

  let ticks: number[] = [];
  $: if (pastData.length > 0) {
    let nonNull = pastData
      .map((v) => v.y)
      .filter((v) => typeof v == 'number' && v != null && v != undefined);
    if (nonNull.length > 0) {
      ticks = [
        nonNull.reduce((curr, v) => Math.min(curr, v), 1e12),
        nonNull.reduce((curr, v) => Math.max(curr, v), -1e12),
      ];
    } else ticks = [];
  }

  let hoveredIndex: number | null = null;

  const yAxisFormat = d3.format('.3~');
</script>

<a
  class="bg-white block mb-2 rounded-md border border-slate-200 {pastData.length ==
  0
    ? 'pointer-events-none'
    : 'hover:bg-slate-50'}"
  on:click={(e) => (expanded = !expanded)}
  href="#"
>
  <div
    class="{typeof element.value === 'string' && element.value.length > 100
      ? 'py-3'
      : 'flex items-center gap-2 py-1'} px-4"
    style="min-height: 4rem;"
    title={pastData.length == 0
      ? ''
      : `Click to ${expanded ? 'hide' : 'show'} recent values`}
  >
    <div class="flex-auto text-xs lg:text-sm">{element.name}</div>
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
          {#if element.value == 'Yes'}<Fa
              class="text-xl text-green-400"
              icon={faCheckCircle}
            />{:else if element.value == 'No'}<Fa
              class="text-xl text-pink-400"
              icon={faXmarkCircle}
            />{:else}{element.value}{/if}
        </div>
        {#if !!element.unit}
          <div class="text-slate-500 text-xs">{element.unit}</div>
        {/if}
      </div>
    {/if}
  </div>
  {#if expanded}
    {#if pastData.length < 2}
      <div class="w-full flex items-center justify-center h-24">
        <div class="text-slate-600 text-sm">No prior data available.</div>
      </div>
    {:else}
      <div class="w-full h-24 px-8 py-4">
        <LayerCake
          x="x"
          y="y"
          data={pastData}
          padding={{ left: 4, bottom: 8 }}
          xDomain={[pastData[0].x, pastData[pastData.length - 1].x]}
          yDomain={ticks.length == 2 ? ticks : [0, 1]}
          custom={{
            hoveredGet: (d) => {
              return d.i == hoveredIndex;
            },
          }}
        >
          <Html pointerEvents={false}>
            <ChartBackground class="bg-slate-100 rounded-md" inset={-4} />
          </Html>
          <Svg>
            <!-- <ShadingX
      highlightFn={(d) => suspectedMissingValue(d, true, false)}
      color={highlightImputedValues ? '#FF725C33' : 'transparent'}
      on:hover={(e) =>
        (hoveredSegment =
          e.detail != null && highlightImputedValues ? e.detail.i : null)}
    />
    <ShadingX
      highlightFn={(d) => suspectedMissingValue(d, false, true)}
      color={highlightHeldValues ? '#FF725C33' : 'transparent'}
      on:hover={(e) =>
        (hoveredSegment =
          e.detail != null && highlightHeldValues ? e.detail.i : null)}
    /> -->
            <AxisX
              gridlines={true}
              tickMarks={false}
              ticks={createXTicks(pastData)}
              formatTick={(t) => formatTimeDelta(t, true)}
              yTick={20}
              color="#999"
              snapTicks={true}
            />
            {#if dataBoolean}
              <ShadingX
                highlightFn={(d) => d.y}
                padding={-8}
                color="#3b82f6"
                mergeSegments
              />
            {:else}
              <AxisY
                gridlines={false}
                tickMarks={false}
                {ticks}
                formatTick={(t) => yAxisFormat(t)}
                textAnchor="end"
                dxTick={-4}
                dyTick="0.5em"
                color="#999"
              />
              <Line stroke="#2563eb" />
            {/if}
            <ShadingX
              highlightFn={(d) => true}
              color="transparent"
              on:hover={(e) =>
                (hoveredIndex = e.detail != null ? e.detail.i : null)}
            />
          </Svg>
          <Html pointerEvents={false}>
            <ChartTooltip
              formatText={(d) =>
                `${formatTimeDelta(d.x)}: ${!!d.rawValue ? d.rawValue : 'missing'}`}
            />
          </Html>
        </LayerCake>
      </div>
    {/if}
  {/if}
</a>
