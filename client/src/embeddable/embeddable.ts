import '../app.css';
import EmbeddableADS from './EmbeddableADS.svelte';

const urlParams = new URLSearchParams(window.location.search);
let patientID = urlParams.get('id');
let dataset = urlParams.get('dataset');
let interfaceType = urlParams.get('interface');
let timestep: number | string | null = urlParams.get('ts');
if (!!timestep) {
  try {
    timestep = parseInt(timestep);
  } catch (e) {
    console.error('invalid timestep index', timestep);
    timestep = null;
  }
}

const app = new EmbeddableADS({
  target: document.body,
  props: {
    initPatientID: patientID,
    initDataset: dataset,
    initInterfaceType: interfaceType,
    initTimestepIndex: timestep,
  },
});

export default app;
