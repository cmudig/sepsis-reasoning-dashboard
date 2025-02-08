<script lang="ts">
  import { onDestroy, onMount, setContext } from 'svelte';
  import { writable, type Writable } from 'svelte/store';
  import type { PatientData } from './lib/patientdata';
  import DataElementPane from './lib/DataElementPane.svelte';
  import PredictiveIndependentPane from './lib/rst/PredictiveIndependentPane.svelte';
  import PrescriptivePeerPane from './lib/rst/PrescriptivePeerPane.svelte';
  import PredictionDependentPane from './lib/rst/PredictionDependentPane.svelte';
  import AiClinicianPane from './lib/rst/AIClinicianPane.svelte';
  import {
    faCheck,
    faChevronDown,
    faChevronLeft,
    faChevronRight,
    faChevronUp,
    faCopy,
    faRightFromBracket,
  } from '@fortawesome/free-solid-svg-icons';
  import Fa from 'svelte-fa';
  import DescriptivePane from './lib/rst/DescriptivePane.svelte';

  let datasets: string[] = [];
  let currentDataset: string | null = null;

  export let initPatientID: string | null = null;
  export let initDataset: string | null = null;
  export let initTimestepIndex: number | null = null;

  let visiblePatientID: string | null = null;
  let patientData: Writable<PatientData> = writable({});
  setContext('patientData', patientData);

  let loadingPatient: boolean = false;
  let patientLoadError: string | null = null;

  let timestepIndex: Writable<number> = writable(0);
  setContext('timestepIndex', timestepIndex);

  let interestingTimestepIndexes: number[] = [];

  let numTimesteps = 0;

  let editedPatientID: string | null = null;
  $: editedPatientID = visiblePatientID;

  enum Panes {
    all = 'All',
    descriptive = 'Similar/Different Features',
    predictive_short_independent = 'Vasopressor Requirement Simple',
    predictive_long_independent = 'Mortality Simple',
    predictive_short_dependent = 'Vasopressor Requirement Interactive',
    predictive_long_dependent = 'Mortality Interactive',
    prescriptive_peer = 'Clinician Treatment Rec',
    prescriptive_outcome = 'Mortality Treatment Rec',
  }
  let visiblePane: Panes = Panes.descriptive;

  function setPatientData(data: {
    id: string;
    data: PatientData;
    num_timesteps: number;
    interesting_indexes?: number[];
  }) {
    visiblePatientID = data.id;
    $patientData = data.data;
    numTimesteps = data.num_timesteps;
    interestingTimestepIndexes = data.interesting_indexes ?? [];
    $timestepIndex =
      initTimestepIndex ??
      (interestingTimestepIndexes.length > 0
        ? interestingTimestepIndexes[0]
        : 0);
    initTimestepIndex = null;
    console.log('patient data:', $patientData);
    patientLoadError = null;
    document.title = `Sepsis AI | Patient ${visiblePatientID}`;
    history.pushState(
      {},
      '',
      `/?dataset=${currentDataset}&id=${visiblePatientID}&ts=${$timestepIndex}`
    );
  }

  async function randomPatient() {
    loadingPatient = true;
    try {
      let randomPatientData = await (
        await fetch(`/dataset/${currentDataset}/patient/random`)
      ).json();
      setPatientData(randomPatientData);
    } catch (e) {
      patientLoadError = `${e}`;
    }
    loadingPatient = false;
  }

  async function searchPatient() {
    loadingPatient = true;
    try {
      let result = await (
        await fetch(`/dataset/${currentDataset}/patient/${editedPatientID}`)
      ).json();
      setPatientData(result);
    } catch (e) {
      patientLoadError = 'No patient found with that ID';
      editedPatientID = visiblePatientID;
    }
    loadingPatient = false;
  }

  onMount(async () => {
    datasets = await (await fetch('/dataset')).json();
    currentDataset = initDataset ?? datasets[0];
    initDataset = null;
  });

  let oldDataset: string | null = null;
  $: if (currentDataset != oldDataset) {
    oldDataset = currentDataset;
    if (!!initPatientID) {
      editedPatientID = initPatientID;
      searchPatient();
      initPatientID = null;
    } else randomPatient();
  }

  let justCopied: boolean = false;
  function copyLink() {
    navigator.clipboard.writeText(
      `https://rst-viewer-dot-ai-clinician.ue.r.appspot.com/?dataset=${currentDataset}&id=${visiblePatientID}&ts=${$timestepIndex}`
    );
    justCopied = true;
    setTimeout(() => (justCopied = false), 5000);
  }
</script>

<main class="w-screen h-screen flex flex-col">
  <div
    class="w-full h-12 grow-0 shrink-0 bg-slate-700 flex py-2 px-4 items-center gap-2"
  >
    <div class="text-white font-bold shrink truncate">Sepsis AI</div>
    <div class="flex-auto" />

    <form
      action="#"
      class="flex items-center gap-2 w-96 max-w-1/2"
      on:submit|preventDefault={() => {
        searchPatient();
        return false;
      }}
    >
      <input
        type="text"
        class="flat-text-input-sm flex-auto"
        bind:value={editedPatientID}
        disabled={loadingPatient}
      />
      {#if editedPatientID != visiblePatientID && !loadingPatient}
        <input type="submit" class="btn btn-dark-blue shrink-0" value="Go" />
        <button
          class="btn btn-dark-slate shrink-0"
          on:click={() => (editedPatientID = visiblePatientID)}>Cancel</button
        >
      {/if}
    </form>
    <button
      class="btn btn-dark-slate"
      disabled={loadingPatient}
      on:click={randomPatient}>Random Patient</button
    >
    <select class="flat-select-dark" bind:value={currentDataset}>
      {#each datasets as dataset}
        <option value={dataset}>{dataset}</option>
      {/each}
    </select>
    <button
      class="px-2 font-bold text-white hover:opacity-50"
      on:click={copyLink}
      class:opacity-50={justCopied}
      disabled={justCopied}
      >{#if justCopied}<Fa icon={faCheck} class="inline mr-1" /> Copied!{:else}<Fa
          icon={faCopy}
          class="inline mr-1"
        /> Copy Link{/if}</button
    >
    <a class="px-2 font-bold text-white hover:opacity-50" href="/logout"
      ><Fa icon={faRightFromBracket} class="inline mr-1" /> Logout</a
    >
  </div>
  <div class="flex-auto w-full flex h-0 relative">
    <div class="flex flex-col w-1/4 px-4 gap-4">
      <div class="shrink-0 w-full pt-4">
        <div class="flex items-center w-full gap-2">
          <div class="text-sm shrink-0">
            <span class="text-slate-600">Hour</span>
            <strong>{$timestepIndex * 4 + 1}</strong>
            <span class="text-slate-600">of</span>
            <strong>{numTimesteps * 4}</strong>
          </div>
          <input
            class="flex-auto w-0"
            type="range"
            min="0"
            max={numTimesteps - 1}
            bind:value={$timestepIndex}
          />
          <button
            class="hover:opacity-50 text-blue-600 ml-2"
            title="Go to the previous {interestingTimestepIndexes.length > 0
              ? 'interesting '
              : ''}timestep"
            disabled={loadingPatient}
            on:click={() => {
              if (interestingTimestepIndexes.length > 0) {
                $timestepIndex =
                  interestingTimestepIndexes.findLast(
                    (t) => t < $timestepIndex
                  ) ?? interestingTimestepIndexes[0];
              } else
                $timestepIndex =
                  ($timestepIndex + numTimesteps - 1) % numTimesteps;
            }}><Fa icon={faChevronLeft} /></button
          >
          <button
            class="hover:opacity-50 text-blue-600"
            title="Go to the next {interestingTimestepIndexes.length > 0
              ? 'interesting '
              : ''}timestep"
            disabled={loadingPatient}
            on:click={() => {
              if (interestingTimestepIndexes.length > 0) {
                $timestepIndex =
                  interestingTimestepIndexes.find((t) => t > $timestepIndex) ??
                  interestingTimestepIndexes[
                    interestingTimestepIndexes.length - 1
                  ];
              } else $timestepIndex = ($timestepIndex + 1) % numTimesteps;
            }}><Fa icon={faChevronRight} /></button
          >
        </div>
      </div>
      <div
        class="flex-auto h-0 w-full overflow-hidden"
        style="min-height: 120px;"
      >
        <DataElementPane section="Demographics" />
      </div>
      <div class="w-full" style="flex-basis: fit-content;">
        <DataElementPane height="50vh" section="Notes" />
      </div>
    </div>
    <div class="h-full w-1/4 pr-4 overflow-hidden">
      <DataElementPane section="State" filterable />
    </div>
    <div class="border-l border-slate-400 p-4 h-full w-1/2 overflow-y-auto">
      <div class="pb-4 flex items-center">
        <select class="flat-select" bind:value={visiblePane}>
          {#each Object.values(Panes) as paneValue}
            <option value={paneValue}>{paneValue}</option>
          {/each}
        </select>
      </div>
      {#if visiblePane == Panes.all || visiblePane == Panes.descriptive}
        <div class="mb-4">
          <DescriptivePane collapsible={visiblePane == Panes.all} />
        </div>
      {/if}
      {#if visiblePane == Panes.all || visiblePane == Panes.predictive_short_independent}
        <div class="mb-4">
          <PredictiveIndependentPane
            shortName="vaso"
            longName="Vasopressor Requirement"
            outcomeDescription="still require vasopressors after 12 hours"
            collapsible={visiblePane == Panes.all}
          />
        </div>
      {/if}
      {#if visiblePane == Panes.all || visiblePane == Panes.predictive_long_independent}
        <div class="mb-4">
          <PredictiveIndependentPane
            shortName="morta"
            longName="Mortality"
            outcomeDescription="have a final discharge outcome of mortality"
            collapsible={visiblePane == Panes.all}
          />
        </div>
      {/if}
      {#if visiblePane == Panes.all || visiblePane == Panes.predictive_short_dependent}
        <div class="mb-4">
          <PredictionDependentPane
            shortName="vaso"
            longName="Vasopressor Requirement"
            outcomeDescription="still require vasopressors after 12 hours"
            collapsible={visiblePane == Panes.all}
          />
        </div>
      {/if}
      {#if visiblePane == Panes.all || visiblePane == Panes.predictive_long_dependent}
        <div class="mb-4">
          <PredictionDependentPane
            shortName="morta"
            longName="Mortality"
            outcomeDescription="have a final discharge outcome of mortality"
            collapsible={visiblePane == Panes.all}
          />
        </div>
      {/if}
      {#if visiblePane == Panes.all || visiblePane == Panes.prescriptive_peer}
        <div class="mb-4">
          <PrescriptivePeerPane collapsible={visiblePane == Panes.all} />
        </div>
      {/if}
      {#if visiblePane == Panes.all || visiblePane == Panes.prescriptive_outcome}
        <div class="mb-4">
          <AiClinicianPane collapsible={visiblePane == Panes.all} />
        </div>
      {/if}
    </div>
    {#if loadingPatient}
      <div
        class="w-full h-full absolute top-0 left-0 flex flex-col items-center justify-center bg-white/80"
      >
        <div class="text-center mb-4">Loading patient...</div>
        <div role="status">
          <svg
            aria-hidden="true"
            class="w-8 h-8 text-gray-200 animate-spin dark:text-gray-600 fill-blue-600"
            viewBox="0 0 100 101"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
          >
            <path
              d="M100 50.5908C100 78.2051 77.6142 100.591 50 100.591C22.3858 100.591 0 78.2051 0 50.5908C0 22.9766 22.3858 0.59082 50 0.59082C77.6142 0.59082 100 22.9766 100 50.5908ZM9.08144 50.5908C9.08144 73.1895 27.4013 91.5094 50 91.5094C72.5987 91.5094 90.9186 73.1895 90.9186 50.5908C90.9186 27.9921 72.5987 9.67226 50 9.67226C27.4013 9.67226 9.08144 27.9921 9.08144 50.5908Z"
              fill="currentColor"
            />
            <path
              d="M93.9676 39.0409C96.393 38.4038 97.8624 35.9116 97.0079 33.5539C95.2932 28.8227 92.871 24.3692 89.8167 20.348C85.8452 15.1192 80.8826 10.7238 75.2124 7.41289C69.5422 4.10194 63.2754 1.94025 56.7698 1.05124C51.7666 0.367541 46.6976 0.446843 41.7345 1.27873C39.2613 1.69328 37.813 4.19778 38.4501 6.62326C39.0873 9.04874 41.5694 10.4717 44.0505 10.1071C47.8511 9.54855 51.7191 9.52689 55.5402 10.0491C60.8642 10.7766 65.9928 12.5457 70.6331 15.2552C75.2735 17.9648 79.3347 21.5619 82.5849 25.841C84.9175 28.9121 86.7997 32.2913 88.1811 35.8758C89.083 38.2158 91.5421 39.6781 93.9676 39.0409Z"
              fill="currentFill"
            />
          </svg>
        </div>
      </div>
    {:else if !!patientLoadError}
      <div
        class="w-full h-full absolute top-0 left-0 flex flex-col items-center justify-center bg-white/80"
      >
        <div class="text-center mb-4 text-red-600 w-1/2">
          Error loading patient data: <div class="font-bold font-mono">
            {patientLoadError}
          </div>
        </div>
      </div>
    {/if}
  </div>
</main>
