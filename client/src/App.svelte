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
    faChevronDown,
    faChevronLeft,
    faChevronRight,
    faChevronUp,
  } from '@fortawesome/free-solid-svg-icons';
  import Fa from 'svelte-fa';
  import DescriptivePane from './lib/rst/DescriptivePane.svelte';

  let datasets: string[] = [];
  let currentDataset: string | null = null;

  let visiblePatientID: string | null = null;
  let patientData: Writable<PatientData> = writable({});
  setContext('patientData', patientData);

  let timestepIndex: Writable<number> = writable(0);
  setContext('timestepIndex', timestepIndex);

  let interestingTimestepIndexes: number[] = [];

  let numTimesteps = 0;

  let editedPatientID: string | null = null;
  $: editedPatientID = visiblePatientID;

  let allCollapsed: boolean = true;

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
      interestingTimestepIndexes.length > 0 ? interestingTimestepIndexes[0] : 0;
    console.log('patient data:', $patientData);
  }

  async function randomPatient() {
    let randomPatientData = await (
      await fetch(`/dataset/${currentDataset}/patient/random`)
    ).json();
    setPatientData(randomPatientData);
  }

  async function searchPatient() {
    try {
      let result = await (
        await fetch(`/dataset/${currentDataset}/patient/${editedPatientID}`)
      ).json();
      setPatientData(result);
    } catch (e) {
      alert('No patient found with that ID.');
      editedPatientID = visiblePatientID;
    }
  }

  onMount(async () => {
    datasets = await (await fetch('/dataset')).json();
    currentDataset = datasets[0];
  });

  let oldDataset: string | null = null;
  $: if (currentDataset != oldDataset) {
    oldDataset = currentDataset;
    randomPatient();
  }
</script>

<main class="w-screen h-screen flex flex-col">
  <div
    class="w-full h-12 grow-0 shrink-0 bg-slate-700 flex py-2 px-4 items-center gap-2"
  >
    <div class="text-white font-bold">Sepsis Reasoning Support Tools</div>
    <div class="flex-auto" />

    <div class="text-white text-sm">
      <span class="text-slate-200">Hour</span>
      <strong>{$timestepIndex * 4 + 1}</strong>
      <span class="text-slate-200">of</span>
      <strong>{numTimesteps * 4}</strong>
    </div>
    <input
      class="w-16 mr-1"
      type="range"
      min="0"
      max={numTimesteps - 1}
      bind:value={$timestepIndex}
    />
    <button
      class="hover:opacity-50 text-white"
      title="Go to the previous interesting timestep"
      on:click={() => {
        if (interestingTimestepIndexes.length > 0) {
          $timestepIndex =
            interestingTimestepIndexes.findLast((t) => t < $timestepIndex) ??
            interestingTimestepIndexes[0];
        } else
          $timestepIndex = ($timestepIndex + numTimesteps - 1) % numTimesteps;
      }}><Fa icon={faChevronLeft} /></button
    >
    <button
      class="hover:opacity-50 text-white mr-2"
      title="Go to the next interesting timestep"
      on:click={() => {
        if (interestingTimestepIndexes.length > 0) {
          $timestepIndex =
            interestingTimestepIndexes.find((t) => t > $timestepIndex) ??
            interestingTimestepIndexes[interestingTimestepIndexes.length - 1];
        } else $timestepIndex = ($timestepIndex + 1) % numTimesteps;
      }}><Fa icon={faChevronRight} /></button
    >
    <button class="btn btn-dark-slate" on:click={randomPatient}
      >Random Patient</button
    >
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
      />
      {#if editedPatientID != visiblePatientID}
        <input type="submit" class="btn btn-dark-blue shrink-0" value="Go" />
        <button
          class="btn btn-dark-slate shrink-0"
          on:click={() => (editedPatientID = visiblePatientID)}>Cancel</button
        >
      {/if}
    </form>
    <select class="flat-select-dark" bind:value={currentDataset}>
      {#each datasets as dataset}
        <option value={dataset}>{dataset}</option>
      {/each}
    </select>
    <a class="px-2 font-bold text-white hover:opacity-50" href="/logout"
      >Logout</a
    >
  </div>
  <div class="flex-auto w-full flex h-0">
    <div class="flex flex-col w-1/4 px-4 gap-4">
      <div class="flex-auto h-0 w-full overflow-hidden">
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
      <div class="px-4 pb-2 flex items-center justify-end">
        <button
          class="hover:opacity-50 text-blue-700 shrink-0 text-sm"
          on:click={() => (allCollapsed = !allCollapsed)}
        >
          {allCollapsed ? 'Expand All' : 'Collapse All'}<Fa
            class="inline ml-2"
            icon={allCollapsed ? faChevronDown : faChevronUp}
          />
        </button>
      </div>
      <div class="mb-4">
        <DescriptivePane collapsed={allCollapsed} />
      </div>
      <div class="mb-4">
        <PredictiveIndependentPane
          shortName="vaso"
          longName="Vasopressor Requirement"
          outcomeDescription="still require prolonged vasopressors after 12 hours"
          collapsed={allCollapsed}
        />
      </div>
      <div class="mb-4">
        <PredictiveIndependentPane
          shortName="morta"
          longName="Mortality"
          outcomeDescription="have a final discharge outcome of mortality"
          collapsed={allCollapsed}
        />
      </div>
      <div class="mb-4">
        <PredictionDependentPane
          shortName="vaso"
          longName="Vasopressor Requirement"
          outcomeDescription="still require prolonged vasopressors after 12 hours"
          collapsed={allCollapsed}
        />
      </div>
      <div class="mb-4">
        <PredictionDependentPane
          shortName="morta"
          longName="Mortality"
          outcomeDescription="have a final discharge outcome of mortality"
          collapsed={allCollapsed}
        />
      </div>
      <div class="mb-4">
        <PrescriptivePeerPane collapsed={allCollapsed} />
      </div>
      <div class="mb-4">
        <AiClinicianPane collapsed={allCollapsed} />
      </div>
    </div>
  </div>
</main>
