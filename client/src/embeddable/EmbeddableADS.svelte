<script lang="ts">
  import { onDestroy, onMount, setContext } from 'svelte';
  import { writable, type Writable } from 'svelte/store';
  import type { PatientData } from '../lib/patientdata';
  import StudyAds from '../study/StudyADS.svelte';
  import DescriptivePane from '../lib/rst/DescriptivePane.svelte';
  import PredictiveIndependentPane from '../lib/rst/PredictiveIndependentPane.svelte';
  import PredictionDependentPane from '../lib/rst/PredictionDependentPane.svelte';
  import PrescriptivePeerPane from '../lib/rst/PrescriptivePeerPane.svelte';
  import AiClinicianPane from '../lib/rst/AIClinicianPane.svelte';
  import TreatmentRecommendationPane from '../lib/new_rst/TreatmentRecommendationPane.svelte';
  import OutcomeOptionsPane from '../lib/new_rst/OutcomeOptionsPane.svelte';
  import PeerOptionsPane from '../lib/new_rst/PeerOptionsPane.svelte';
  import LoadingPane from '../lib/new_rst/LoadingPane.svelte';
  import UncommonActionsPane from '../lib/new_rst/UncommonActionsPane.svelte';

  export let initPatientID: string | null = null;
  export let initDataset: string | null = null;
  export let initTimestepIndex: number | null = null;
  export let initInterfaceType: string | null = null;
  export let parentURL: string | null = null;

  let visiblePatientID: string | null = null;
  let currentDataset: string | null = null;
  let adsInterface: string = 'descriptive';
  let patientData: Writable<PatientData> = writable({});
  setContext('patientData', patientData);

  let loadingPatient: boolean = false;
  let patientLoadError: string | null = null;

  let timestepIndex: Writable<number> = writable(0);
  setContext('timestepIndex', timestepIndex);

  function setPatientData(data: {
    id: string;
    data: PatientData;
    num_timesteps: number;
    interesting_indexes?: number[];
  }) {
    visiblePatientID = data.id;
    $patientData = data.data;
    $timestepIndex = initTimestepIndex ?? 0;
    initTimestepIndex = null;
    adsInterface = initInterfaceType ?? 'descriptive';
    initInterfaceType = null;
    console.log('patient data:', $patientData);
    patientLoadError = null;
    document.title = `Sepsis AI | Patient ${visiblePatientID}`;
  }

  let observer: ResizeObserver | undefined;

  onMount(async () => {
    currentDataset = initDataset;
    initDataset = null;

    loadingPatient = true;
    try {
      let result = await (
        await fetch(`/dataset/${currentDataset}/patient/${initPatientID}`)
      ).json();
      setPatientData(result);
      visiblePatientID = initPatientID;
      initPatientID = null;
    } catch (e) {
      patientLoadError = 'No patient found with that ID';
      visiblePatientID = null;
    }
    loadingPatient = false;

    observer = new ResizeObserver(handleResize);

    observer.observe(document.body);
  });

  onDestroy(() => {
    if (!!observer) {
      observer.unobserve(document.body);
      observer = undefined;
    }
  });

  function handleResize() {
    if (window.parent) {
      window.parent.postMessage(
        {
          type: 'embeddable-resize',
          height: document.body.scrollHeight,
        },
        new URL(parentURL ?? 'http://localhost:4999').origin
      );
    }
  }
</script>

<div class="p-2 bg-white">
  {#if !!$patientData}
    {#if adsInterface == 'descriptive'}
      <DescriptivePane collapsible={false} showSummary={false} />
    {/if}
    {#if adsInterface == 'predictive_vaso_independent'}
      <PredictiveIndependentPane
        shortName="vaso"
        longName="Vasopressor Requirement"
        outcomeDescription="require vasopressors after 12 hours"
        collapsible={false}
        showGroundTruth={false}
        showSummary={false}
      />
    {/if}
    {#if adsInterface == 'predictive_morta_independent'}
      <PredictiveIndependentPane
        shortName="morta"
        longName="Mortality"
        outcomeDescription="have a final discharge outcome of mortality"
        collapsible={false}
        showGroundTruth={false}
        showSummary={false}
      />
    {/if}
    {#if adsInterface == 'predictive_vaso_dependent'}
      <PredictionDependentPane
        shortName="vaso"
        longName="Vasopressor Requirement"
        outcomeDescription="require vasopressors after 12 hours"
        collapsible={false}
        showGroundTruth={false}
        showSummary={false}
      />
    {/if}
    {#if adsInterface == 'predictive_morta_dependent'}
      <PredictionDependentPane
        shortName="morta"
        longName="Mortality"
        outcomeDescription="have a final discharge outcome of mortality"
        collapsible={false}
        showGroundTruth={false}
        showSummary={false}
      />
    {/if}
    {#if adsInterface == 'prescriptive_peer'}
      <PrescriptivePeerPane
        collapsible={false}
        showGroundTruth={false}
        showSummary={false}
      />
    {/if}
    {#if adsInterface == 'prescriptive_outcome'}
      <AiClinicianPane
        collapsible={false}
        showGroundTruth={false}
        showSummary={false}
      />
    {/if}
    {#if adsInterface == 'treatment_recommendation'}
      <TreatmentRecommendationPane
        collapsible={false}
        showGroundTruth={false}
        showSummary={false}
      />
    {/if}
    {#if adsInterface == 'outcome_options'}
      <OutcomeOptionsPane
        collapsible={false}
        shortName="morta"
        longName="Mortality"
        outcomeDescription="have a final discharge outcome of mortality"
        showGroundTruth={false}
        showSummary={false}
        minimumSampleSize={10}
      />
    {/if}
    {#if adsInterface == 'best_options'}
      <OutcomeOptionsPane
        collapsible={false}
        shortName="morta"
        longName="Mortality"
        outcomeDescription="have a final discharge outcome of mortality"
        showGroundTruth={false}
        showSummary={false}
        balanceFiltering
        rankOptions="best"
      />
    {/if}
    {#if adsInterface == 'worst_options'}
      <OutcomeOptionsPane
        collapsible={false}
        shortName="morta"
        longName="Mortality"
        outcomeDescription="have a final discharge outcome of mortality"
        showGroundTruth={false}
        showSummary={false}
        balanceFiltering
        rankOptions="worst"
        warningStyle
      />
    {/if}
    {#if adsInterface == 'peer_options'}
      <div class="mb-4">
        <PeerOptionsPane
          collapsible={false}
          shortName="morta"
          showGroundTruth={false}
        />
      </div>
    {/if}
    {#if adsInterface == 'uncommon_actions'}
      <div class="mb-4">
        <UncommonActionsPane collapsible={false} showGroundTruth={false} />
      </div>
    {/if}
  {/if}
  {#if loadingPatient}
    <LoadingPane
      showInset={initInterfaceType == 'outcome_options' ||
        initInterfaceType == 'peer_options'}
    />
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
