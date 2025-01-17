<script lang="ts">
  export let csrf;
  export let errorMessage = '';
</script>

<main class="w-screen h-screen flex flex-col">
  <div
    class="w-full h-12 grow-0 shrink-0 bg-slate-700 flex py-2 px-4 items-center text-white font-bold"
  >
    Sepsis RST Viewer
  </div>
  <div
    class="flex-auto w-full flex justify-center items-center"
    style="min-height: 400px;"
  >
    <form
      class="w-1/2 p-4 rounded bg-slate-100"
      style="min-width: 400px;"
      method="POST"
      action="/login"
    >
      <fieldset id="login" class="bg-transparent">
        <legend class="font-bold">Sign In</legend>
        {#if !!errorMessage}
          <div class="p-2 my-2 rounded bg-red-100 text-small">
            {errorMessage}
          </div>
        {/if}
        <div class="mt-2">
          <label class="text-sm" for="user_id">User ID</label>
          <input
            class="flat-text-input w-full"
            type="username"
            name="user_id"
            id="user_id"
          />
        </div>
        <div class="mt-2">
          <label class="text-sm" for="password">Password</label>
          <input
            class="flat-text-input w-full"
            type="password"
            name="password"
            id="password"
          />
        </div>
        <div class="mt-2">
          <label class="text-sm cursor-pointer"
            ><input type="checkbox" name="remember" /> Remember me</label
          >
        </div>
      </fieldset>
      <input type="hidden" name="csrf_token" value={csrf} />
      <div class="">
        <input
          class="mt-2 btn btn-blue cursor-pointer"
          type="submit"
          value="Sign In"
        />
      </div>
    </form>
  </div>
</main>
