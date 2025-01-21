<script lang="ts">
  import { getContext } from 'svelte';
  import type { Writable } from 'svelte/store';
  import type { PatientData } from '../patientdata';
  import Fa from 'svelte-fa';
  import {
    faBedPulse,
    faChevronDown,
    faChevronRight,
  } from '@fortawesome/free-solid-svg-icons';
  import * as d3 from 'd3';
  import ExplanationView from './ExplanationView.svelte';
  import CategoryBar from '../charts/CategoryBar.svelte';

  export let showGroundTruth: boolean = true;

  export let colorSchemes = [
    d3.schemeBlues[3],
    d3.schemePurples[3],
    d3.schemeOranges[3],
  ];

  type Recommendation = {
    recommendation: { tx: string; value: string; description: string }[];
    sample_size: number;
    ground_truth?: {
      tx: string;
      label: string;
    }[];
    severity_range: {
      min: number;
      max: number;
    };
  };

  let patientData: Writable<PatientData> = getContext('patientData');
  let timestepIndex: Writable<number> = getContext('timestepIndex');

  let recommendation: Recommendation | undefined;
  $: if (!!$patientData && !!$patientData['AI Clinician']) {
    recommendation =
      $patientData['AI Clinician'].timesteps![$timestepIndex].data;
  } else {
    recommendation = undefined;
  }
</script>

{#if !!recommendation}
  <div class="w-full rounded-md bg-blue-50 p-4">
    <div class="pb-2 text-blue-700">
      <Fa icon={faBedPulse} class="inline mr-2" /><span
        class="font-bold uppercase font-mono mr-2"
        >Sepsis AI Recommendation</span
      >
    </div>
    <div class="measure">
      Sepsis AI recommends
      {#each recommendation.recommendation.slice(0, recommendation.recommendation.length - 1) as rec (rec.tx)}
        <strong>{rec.description}, </strong>
      {/each}and
      <strong
        >{recommendation.recommendation[
          recommendation.recommendation.length - 1
        ].description}</strong
      > over the next 4 hours.
    </div>
    <ExplanationView>
      The recommendation is based on {recommendation.sample_size} patients who had
      a similar SOFA score ({recommendation.severity_range.min} - {recommendation
        .severity_range.max}) as this patient and who received the recommended
      treatment. These patients had the greatest improvement in risk of
      mortality and extended ICU stay over the next 4 hours within a set of 100
      similar patients.
    </ExplanationView>
    {#if showGroundTruth && !!recommendation.ground_truth}
      <div class="mt-4 text-sm text-blue-700">Ground truth:</div>
      {#each recommendation.ground_truth as gt, i (gt.tx)}
        <div class="mt-2 text-sm">
          <span
            class="font-bold"
            style="color: {colorSchemes[i][colorSchemes[i].length - 1]};"
            >{gt.tx}</span
          >: {gt.label}
        </div>
      {/each}
    {/if}
  </div>
{/if}
