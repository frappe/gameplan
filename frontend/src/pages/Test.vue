<template>
  <div class="p-14">
    <pre
      >{{ teams }}
    </pre>
  </div>
</template>
<script setup lang="ts">
import useFrappeFetch from 'frappe-ui/src/data-fetching/useFrappeFetch'
import useList from 'frappe-ui/src/data-fetching/useList'

// const ctx = useFrappeFetch('/api/v2/method/ping')
// const ctx = useFrappeFetch('/api/v2/method/throw_error')
// error status codes: 400, 401, 403, 404, 500
const teams = useList('GP Team', { fields: ['name', 'title'], filters: {} })
</script>
