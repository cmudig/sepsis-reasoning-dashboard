import './app.css';
import App from './App.svelte';

const urlParams = new URLSearchParams(window.location.search);
let patientId = urlParams.get('id');
let dataset = urlParams.get('dataset');
let timestep: number | string | null = urlParams.get('ts');
if (!!timestep) {
  try {
    timestep = parseInt(timestep);
  } catch (e) {
    console.error('invalid timestep index', timestep);
    timestep = null;
  }
}

const app = new App({
  target: document.getElementById('app'),
  props: {
    initPatientID: patientId,
    initDataset: dataset,
    initTimestepIndex: timestep,
  },
});

export default app;
