import '../app.css';
import Login from './Login.svelte';

let csrf = document.getElementsByName('csrf-token')[0].content;
let errorMessage = document.getElementsByName('open-template-params')[0]
  .content;
const urlParams = new URLSearchParams(window.location.search);
let next = urlParams.get('next');

const app = new Login({
  target: document.body,
  props: {
    csrf,
    errorMessage,
    next,
  },
});

export default app;
