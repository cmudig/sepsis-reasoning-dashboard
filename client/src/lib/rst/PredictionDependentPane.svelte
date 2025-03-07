<script lang="ts">
  import { getContext } from 'svelte';
  import type { Writable } from 'svelte/store';
  import type { PatientData } from '../patientdata';
  import Fa from 'svelte-fa';
  import {
    faBedPulse,
    faChevronDown,
    faChevronRight,
    faChevronUp,
  } from '@fortawesome/free-solid-svg-icons';
  import * as d3 from 'd3';
  import CategoryBar from '../charts/CategoryBar.svelte';
  import Tooltip from '../utils/Tooltip.svelte';

  export let shortName: string = '';
  export let longName: string = '';
  export let outcomeDescription: string = '';

  export let showGroundTruth: boolean = true;
  export let showSummary: boolean = true;
  export let collapsible: boolean = true;

  export let collapsed: boolean = collapsible;
  $: if (!collapsible) collapsed = false;

  export let colorSchemes = [
    d3.schemeBlues[3],
    d3.schemePurples[3],
    d3.schemeOranges[3],
  ];

  type OutcomePrediction = {
    policy?: { tx: string; value: string }[];
    sample_size: number;
    prediction: {
      mean: number;
      std: number;
      pvalue?: number;
    };
  };
  type TreatmentOutcomePrediction = {
    average: OutcomePrediction;
    treatment_names: string[][];
    predictions: OutcomePrediction[];
    ground_truth?: string;
    severity_range: {
      min: number;
      max: number;
    };
  };

  const TreatmentPolicyNames: { [key: string]: string[] } = {
    Volume: [
      '< 100 mL Fluids',
      '100 mL - 1 L Fluids',
      '> 1 L Fluids',
      'Diuretics',
    ],
    Vasopressors: ['None', 'One', 'Multiple'],
  };

  let patientData: Writable<PatientData> = getContext('patientData');
  let timestepIndex: Writable<number> = getContext('timestepIndex');

  // let visibleTarget: string = 'Mortality';

  let prediction: TreatmentOutcomePrediction | undefined;
  let selectedPolicy: (string | null)[] = [null, null];
  let policyPrediction: OutcomePrediction | null = null;
  $: if (
    !!$patientData &&
    !!shortName &&
    !!$patientData[`predictive_${shortName}_dependent`]
  ) {
    prediction =
      $patientData[`predictive_${shortName}_dependent`].timesteps![
        $timestepIndex
      ].data;
    selectedPolicy = [null, null];
  } else {
    prediction = undefined;
  }

  $: if (!!prediction) {
    policyPrediction =
      prediction.predictions.find((p) =>
        p.policy?.every((x, i) => x.value == selectedPolicy[i])
      ) ?? null;
  } else {
    policyPrediction = null;
  }

  const probabilityFormat = d3.format('.0~%');

  function riskDescription(mean: number): string {
    if (mean <= 0.01) return 'exceptionally unlikely';
    else if (mean <= 0.1) return 'very unlikely';
    else if (mean <= 0.33) return 'unlikely';
    else if (mean <= 0.66) return 'about as likely as not';
    else if (mean <= 0.9) return 'likely';
    else if (mean <= 0.99) return 'very likely';
    else return 'virtually certain';
  }
</script>

{#if !!prediction}
  <div class="w-full rounded-md bg-blue-50 p-4">
    <div class="flex items-center w-full gap-4">
      <div class="text-blue-700 flex-auto">
        <Fa icon={faBedPulse} class="inline mr-2" /><span
          class="font-bold uppercase font-mono mr-2">Sepsis AI</span
        >
        Risk of {longName}
        <Tooltip
          hoverTargetClass="inline text-blue-700 hover:opacity-50 px-1"
          title="This AI uses outcomes of similar patients to calculate the risk that your patient will {outcomeDescription} given the treatment plan you select."
        />
      </div>
      {#if showSummary}
        <div class="text-sm">
          {prediction.predictions.length} option{prediction.predictions
            .length != 1
            ? 's'
            : ''}, {prediction.predictions.filter(
            (p) => (p.prediction.pvalue ?? 1) <= 0.05
          ).length} significantly different
        </div>
      {/if}
      {#if collapsible}
        <button
          class="hover:opacity-50 text-blue-700 shrink-0"
          on:click={() => (collapsed = !collapsed)}
        >
          <Fa icon={collapsed ? faChevronDown : faChevronUp} />
        </button>
      {/if}
    </div>
    {#if !collapsed}
      <div class="mt-2 flex gap-4 w-full items-start">
        <div class="flex-auto basis-0">
          <div class="measure">
            {#if selectedPolicy.some((p) => p === null)}
              <span class="text-slate-600"
                >Select treatments on the right to see the risk that the patient
                will <strong>{outcomeDescription}</strong> if you give that treatment.</span
              >
            {:else if !!policyPrediction}
              This treatment plan was <Tooltip
                title="{policyPrediction.sample_size}/100 similar patients"
                ><span class="hoverable-text"
                  >{#if policyPrediction.sample_size > 50}very common{:else if policyPrediction.sample_size > 20}somewhat
                    common{:else}uncommon{/if}</span
                ></Tooltip
              >
              among similar patients.
            {:else}
              <span class="text-slate-600"
                >Predictions cannot be shown for this treatment plan because not
                enough similar patients received it.</span
              >
            {/if}
          </div>
          {#if !!policyPrediction}
            <!-- {@const targetPrediction = policyPrediction.predictions.find(
              (p) => p.target == visibleTarget
            )}
            <div class="w-full flex gap-3">
              {#each policyPrediction.predictions as predTarget (predTarget.target)}
                <button
                  class="flex-auto basis-1 rounded my-2 py-1 text-sm text-center {visibleTarget ==
                  predTarget.target
                    ? 'bg-slate-600 text-white font-bold hover:bg-slate-700'
                    : 'text-slate-700 hover:bg-slate-300'}"
                  on:click={() => (visibleTarget = predTarget.target)}
                  >{predTarget.target}</button
                >
              {/each}
            </div> -->
            <div class="measure mt-2">
              Similar patients who received this treatment were <Tooltip
                title="{probabilityFormat(
                  policyPrediction.prediction.mean
                )} chance"
                ><span
                  class="font-bold hoverable-text {policyPrediction.prediction
                    .mean > 0.66
                    ? 'text-red-600'
                    : policyPrediction.prediction.mean > 0.33
                      ? 'text-yellow-600'
                      : 'text-green-600'}"
                  >{riskDescription(policyPrediction.prediction.mean)}</span
                ></Tooltip
              > to {outcomeDescription},
              {#if (policyPrediction.prediction.pvalue ?? 0) > 0.05}
                about the same as
              {:else if policyPrediction.prediction.mean > (prediction.average.prediction.mean ?? 0)}
                <strong>significantly worse</strong> than
              {:else}
                <strong>significantly better</strong> than
              {/if}
              <Tooltip
                title="{probabilityFormat(
                  prediction.average.prediction.mean
                )} chance on average"
                ><span class="hoverable-text">other treatments</span></Tooltip
              >.
            </div>
          {/if}
        </div>
        <div class="rounded-md bg-blue-100 p-4 flex flex-col gap-4 w-1/2">
          <div class="text-sm">Treatment options:</div>
          {#each ['Volume', 'Vasopressors'] as tx, i}
            <div class="w-full">
              <div
                class="font-bold text-sm uppercase"
                style="color: {colorSchemes[i][colorSchemes[i].length - 1]};"
              >
                {tx}
              </div>
              <div class="mt-1 grid gap-2 w-full grid-cols-1">
                {#each TreatmentPolicyNames[tx] as policyVal, policyIdx}
                  <button
                    class="rounded-md py-2 px-4 text-xs {selectedPolicy[i] ==
                    policyVal
                      ? 'text-white font-bold'
                      : 'bg-blue-50 hover:bg-blue-200'}"
                    class:opacity-60={selectedPolicy.every(
                      (s, pi) => pi == i || s !== null
                    ) &&
                      !prediction.predictions.find((p) =>
                        p.policy?.every(
                          (x, j) =>
                            x.value == (j == i ? policyVal : selectedPolicy[j])
                        )
                      )}
                    style={selectedPolicy[i] == policyVal
                      ? `background-color: ${colorSchemes[i][colorSchemes[i].length - 1]};`
                      : ''}
                    on:click={() =>
                      (selectedPolicy = [
                        ...selectedPolicy.slice(0, i),
                        selectedPolicy[i] == policyVal ? null : policyVal,
                        ...selectedPolicy.slice(i + 1),
                      ])}
                    >{prediction.treatment_names?.[i]?.[policyIdx] ??
                      policyVal}</button
                  >
                {/each}
              </div>
            </div>
          {/each}
        </div>
      </div>
      {#if showGroundTruth && !!prediction.ground_truth}
        <div class="mt-4 text-sm text-blue-700">
          Ground truth: <strong>{prediction.ground_truth}</strong>
        </div>
      {/if}
    {/if}
  </div>
{/if}
