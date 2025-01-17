import '../app.css';
import Login from './Login.svelte';

let csrf = document.getElementsByName('csrf-token')[0].content;
let errorMessage = document.getElementsByName('open-template-params')[0]
  .content;

const app = new Login({
  target: document.body,
  props: {
    csrf,
    errorMessage,
  },
});

export default app;
