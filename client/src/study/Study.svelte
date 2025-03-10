<script lang="ts">
  import { writable, type Writable } from 'svelte/store';
  import DataElementPane from '../lib/DataElementPane.svelte';
  import type { PatientData } from '../lib/patientdata';
  import { onMount, setContext } from 'svelte';
  import type { Stimulus, StudyProtocol } from '../lib/studydata';
  import StudyAds from './StudyADS.svelte';
  import {
    faBedPulse,
    faChevronLeft,
    faRightFromBracket,
    faUndo,
  } from '@fortawesome/free-solid-svg-icons';
  import Fa from 'svelte-fa';
  import { formatText } from '../lib/utils/utils';
  import { dispatch } from 'd3';

  let patientData: Writable<PatientData> = writable({});
  setContext('patientData', patientData);

  let timestepIndex: Writable<number> = writable(0);
  setContext('timestepIndex', timestepIndex);

  let allPatients: PatientData[] = [];
  let stimulusIndex: number = 0;
  let currentStimulus: Stimulus | null = null;

  let studyProtocol: StudyProtocol | null = null;

  let loadingPatient: boolean = false;
  let patientLoadError: string | null = null;

  enum Phase {
    consent,
    pre_survey,
    intro,
    cases,
    debrief,
  }
  let currentPhase: Phase = Phase.consent;

  let showingPostStimulusQuestions: boolean = false;

  $: if (!!studyProtocol && allPatients.length > stimulusIndex) {
    currentStimulus = studyProtocol.patients[stimulusIndex];
    $patientData = allPatients[stimulusIndex];
    console.log($patientData, $timestepIndex);
    $timestepIndex = currentStimulus.ts;
  } else {
    currentStimulus = null;
    $patientData = {};
  }

  onMount(async () => {
    loadingPatient = true;
    try {
      studyProtocol = await (await fetch('/study_protocol')).json();
      currentPhase = Phase.consent;
      allPatients = await Promise.all(
        studyProtocol!.patients.map(
          async (p) =>
            (
              await (
                await fetch(`/dataset/${p.dataset}/patient/${p.id}`)
              ).json()
            ).data
        )
      );
    } catch (e) {
      patientLoadError = `${e}`;
    }
    loadingPatient = false;
  });

  $: if (
    !!studyProtocol &&
    currentPhase == Phase.consent &&
    !studyProtocol?.text.consent
  )
    currentPhase = Phase.pre_survey;
  $: if (
    !!studyProtocol &&
    currentPhase == Phase.pre_survey &&
    !studyProtocol?.text.pre_survey_link
  )
    currentPhase = Phase.intro;
  $: if (
    !!studyProtocol &&
    currentPhase == Phase.intro &&
    !studyProtocol?.text.intro_text
  )
    currentPhase = Phase.cases;

  let stimulusView: HTMLElement;

  function advanceStimulus() {
    stimulusIndex++;
    showingPostStimulusQuestions = false;
    if (stimulusIndex == allPatients.length) {
      currentPhase = Phase.debrief;
    } else if (!!stimulusView) {
      setTimeout(() => stimulusView.scrollTo({ top: 0, behavior: 'smooth' }));
    }
  }
</script>

<main class="w-screen h-screen flex flex-col">
  <div
    class="w-full h-12 grow-0 shrink-0 bg-slate-700 flex py-2 px-4 items-center text-white"
  >
    <div class="font-bold">Decision-Making in Sepsis</div>
    <div class="flex-auto" />
    {#if !!studyProtocol && studyProtocol.dev_mode}
      <div
        class="rounded bg-orange-600 text-white text-sm font-bold px-1.5 py-0.5 mx-2"
      >
        Dev Mode
      </div>
    {/if}
    {#if !!currentStimulus && currentPhase >= Phase.cases}
      <button
        class="px-2 font-bold text-white hover:opacity-50 disabled:opacity-30"
        disabled={stimulusIndex == 0}
        on:click={() => {
          if (confirm('Are you sure you want to go back?')) stimulusIndex--;
        }}><Fa icon={faUndo} class="inline mr-1" /> Go Back</button
      >
      <div class="mx-2">
        Patient {stimulusIndex + 1} of {studyProtocol?.patients.length}
      </div>
    {/if}
    <a class="px-2 font-bold text-white hover:opacity-50" href="/logout"
      ><Fa icon={faRightFromBracket} class="inline mr-1" /> Logout</a
    >
  </div>
  <div class="flex-auto w-full flex h-0 relative">
    {#if currentPhase == Phase.debrief && !!studyProtocol}
      <div class="w-full h-full flex justify-center overflow-y-auto">
        <div class="w-1/2 max-w-full" style="min-width: 600px;">
          <div class="py-4">
            You have now completed the decision-making portion of the study.
            Below you can see all of the patients and Sepsis AI interfaces that
            were shown to you.
          </div>
          <div class="pb-4">
            {#each studyProtocol.patients as patient, i}
              <div class="pt-2 border-t border-slate-400 mt-2">
                <StudyAds
                  currentStimulus={patient}
                  showPrompt={false}
                  {studyProtocol}
                  patientData={writable(allPatients[i])}
                  timestepIndex={writable(patient.ts)}
                />
              </div>
            {/each}
          </div>
        </div>
      </div>
    {:else if currentPhase == Phase.cases}
      <div class="flex flex-col w-1/4 px-4 gap-4">
        <div class="shrink-0 w-full pt-4">
          <div class="flex items-center w-full gap-2">
            <div class="font-bold shrink-0">
              <span class="text-slate-600">Hour</span>
              {($timestepIndex + 1) * 4}
              <span class="text-slate-600">in the ICU</span>
            </div>
          </div>
        </div>
        <div class="flex-auto h-0 w-full overflow-hidden">
          <DataElementPane section="Demographics" studyEnvironment />
        </div>
      </div>
      <div class="h-full w-1/4 pr-4 overflow-hidden">
        <DataElementPane
          section="State"
          title="Patient Data"
          filterable
          studyEnvironment
        />
      </div>
      <div
        class="border-l border-slate-400 p-4 h-full w-1/2 overflow-y-auto"
        bind:this={stimulusView}
      >
        <StudyAds
          {currentStimulus}
          {studyProtocol}
          {patientData}
          {timestepIndex}
        />
        {#if !!currentStimulus}
          <div
            class="flex items-center justify-center w-full p-4 gap-2 flex-wrap whitespace-nowrap"
          >
            <div>Describe your recommendation verbally, then</div>
            <button
              class="btn btn-blue max-w-full"
              on:click={(e) => {
                if (!!studyProtocol?.text?.post_patient_items) {
                  showingPostStimulusQuestions = true;
                } else advanceStimulus();
              }}>Click Here to Continue</button
            >
          </div>
        {/if}
      </div>
    {/if}
    {#if loadingPatient}
      <div
        class="w-full h-full absolute top-0 left-0 flex flex-col items-center justify-center bg-white/80"
      >
        <div class="text-center mb-4">Loading study...</div>
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
          Error loading study data: <div class="font-bold font-mono">
            {patientLoadError}
          </div>
        </div>
      </div>
    {/if}
    {#if (showingPostStimulusQuestions || currentPhase == Phase.intro || currentPhase == Phase.consent || currentPhase == Phase.pre_survey) && !!studyProtocol}
      <!-- svelte-ignore a11y-no-noninteractive-element-interactions -->
      <div
        class="w-full h-full absolute top-0 left-0 bg-black/60 flex items-center justify-center"
        on:click={showingPostStimulusQuestions
          ? () => (showingPostStimulusQuestions = false)
          : undefined}
        on:keypress={showingPostStimulusQuestions
          ? (e) => {
              if (e.key === 'Escape') showingPostStimulusQuestions = false;
            }
          : undefined}
        role="region"
        aria-label="Click to dismiss"
        tabindex="-1"
      >
        <!-- svelte-ignore a11y-no-noninteractive-element-interactions -->
        <div
          class="w-1/2 p-8 rounded-md bg-white flex flex-col"
          style="min-width: 400px; max-height: 70%;"
          on:click|stopPropagation={() => {}}
          on:keypress={(e) => {}}
          role="region"
          tabindex="-1"
        >
          {#if currentPhase == Phase.intro}
            <div class="flex-auto min-h-0 overflow-y-auto">
              <div class="mb-4 font-bold">Study Overview</div>
              <div class="mb-4">
                {@html formatText(studyProtocol?.text.intro_text ?? '')}
              </div>
              <div class="w-full rounded-md bg-blue-50 p-4 mb-2">
                <div class="text-blue-700 flex-auto">
                  <Fa icon={faBedPulse} class="inline mr-2" /><span
                    class="font-bold uppercase font-mono mr-2">Sepsis AI</span
                  >
                </div>
              </div>
              <div class="mb-4">
                During some of the cases, you may see a box labeled "Sepsis AI"
                with supporting information. This information comes from an AI
                system that was trained on a database of over 14,000 patients to
                identify similar patients to the one you're treating. It is
                designed to give you information about what happened to those
                prior patients to help you make your recommendation. This model
                has been validated by expert clinicians, and the information it
                provides is generally accurate.
              </div>
            </div>
            <div class="flex items-center justify-center w-full pt-4 shrink-0">
              <button
                class="btn btn-blue max-w-full"
                on:click={(e) => {
                  currentPhase++;
                }}>Continue</button
              >
            </div>
          {:else if currentPhase == Phase.pre_survey}
            <div class="flex-auto min-h-0 overflow-y-auto">
              <div class="mb-4 font-bold">Pre-Survey</div>
              <div class="mb-4">
                Please <a
                  class="text-blue-500"
                  href={studyProtocol.text.pre_survey_link}
                  target="_blank">click this link</a
                > to complete a brief survey before the decision-making portion of
                the study.
              </div>
            </div>
            <div class="flex items-center justify-center w-full pt-4 shrink-0">
              <button
                class="btn btn-blue max-w-full"
                on:click={(e) => {
                  currentPhase++;
                }}>Continue when survey is completed</button
              >
            </div>
          {:else if currentPhase == Phase.consent}
            <div class="flex-auto min-h-0 overflow-y-auto">
              <div class="mb-4 font-bold">
                Decision-Making in Sepsis: Informed Consent
              </div>
              <div class="mb-4">
                {@html formatText(studyProtocol?.text.consent ?? '')}
              </div>
            </div>
            <div class="flex items-center justify-center w-full pt-4 shrink-0">
              <button
                class="btn btn-blue max-w-full"
                on:click={(e) => {
                  currentPhase++;
                }}>Yes, Continue</button
              >
            </div>
          {:else}
            <div class="mb-4">
              <button
                class="hover:opacity-50 text-blue-500"
                on:click={() => (showingPostStimulusQuestions = false)}
              >
                <Fa icon={faChevronLeft} class="inline mr-2" /> Back
              </button>
            </div>
            <div class="overflow-y-auto min-h-0 flex-auto">
              <div class="mb-4 text-sm">
                Please verbally answer the following questions.
              </div>
              {#each studyProtocol?.text?.post_patient_items ?? [] as item}
                {#if !(item.ads_only ?? false) || currentStimulus?.ads != 'none'}
                  <div class="mb-8">
                    <div class="mb-1 font-bold">{item.question}</div>
                    {#if !!item.answer_instruction}
                      <div class="text-slate-600">
                        {item.answer_instruction}
                      </div>
                    {/if}
                  </div>
                {/if}
              {/each}
            </div>
            <div class="flex items-center justify-center w-full pt-4">
              <button
                class="btn btn-blue max-w-full"
                on:click={(e) => {
                  advanceStimulus();
                }}>Click here to continue after answering</button
              >
            </div>
          {/if}
        </div>
      </div>
    {/if}
  </div>
</main>
