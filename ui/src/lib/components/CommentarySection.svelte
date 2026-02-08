<script lang="ts">
	import { selectedVerse } from '$lib/stores/selection';
	import { getCached, setCached, commentaryKey } from '$lib/stores/cache';
	import { generateCommentary } from '$lib/api/ollama';
	import { ChevronDown, ChevronRight, MessageSquare, RefreshCw } from 'lucide-svelte';

	let expanded = false;
	let loading = false;
	let commentary: string | null = null;
	let error: string | null = null;

	$: if ($selectedVerse && expanded && !commentary) {
		loadCommentary();
	}

	async function loadCommentary() {
		if (!$selectedVerse) return;

		const cacheKey = commentaryKey($selectedVerse.verse_ref, $selectedVerse.translation);

		// Check cache first
		const cached = getCached<string>(cacheKey);
		if (cached) {
			commentary = cached;
			return;
		}

		loading = true;
		error = null;

		try {
			const result = await generateCommentary(
				$selectedVerse.text,
				$selectedVerse.verse_ref,
				$selectedVerse.translation.toUpperCase()
			);

			commentary = result;
			setCached(cacheKey, result);
		} catch (err) {
			console.error('Commentary generation failed:', err);
			error = 'Failed to generate commentary. Please try again.';
		} finally {
			loading = false;
		}
	}

	function toggle() {
		expanded = !expanded;
	}

	// Reset when verse changes
	$: if ($selectedVerse) {
		commentary = null;
		error = null;
		expanded = false;
	}
</script>

<div class="commentary-section bg-white rounded-lg border border-gray-200 overflow-hidden">
	<!-- Header -->
	<button
		on:click={toggle}
		class="w-full px-4 py-3 flex items-center justify-between hover:bg-gray-50 transition-colors"
	>
		<div class="flex items-center gap-2">
			<MessageSquare class="h-4 w-4 text-primary-600" />
			<h3 class="text-sm font-semibold text-gray-800">Commentary</h3>
		</div>
		{#if expanded}
			<ChevronDown class="h-4 w-4 text-gray-400" />
		{:else}
			<ChevronRight class="h-4 w-4 text-gray-400" />
		{/if}
	</button>

	<!-- Content -->
	{#if expanded}
		<div class="px-4 py-3 border-t border-gray-200 bg-gray-50">
			{#if loading}
				<div class="flex items-center gap-2 text-sm text-gray-600">
					<RefreshCw class="h-4 w-4 animate-spin" />
					Generating commentary...
				</div>
			{:else if error}
				<div class="text-sm text-red-600 bg-red-50 border border-red-200 rounded p-2">
					{error}
					<button
						on:click={loadCommentary}
						class="mt-2 text-red-700 hover:text-red-800 font-medium underline"
					>
						Retry
					</button>
				</div>
			{:else if commentary}
				<div class="prose prose-sm max-w-none text-gray-700 leading-relaxed">
					{@html commentary.replace(/\n\n/g, '</p><p class="mt-3">')}
				</div>
			{:else}
				<button
					on:click={loadCommentary}
					class="w-full py-2 px-4 text-sm text-primary-700 bg-primary-50 hover:bg-primary-100
						   border border-primary-200 rounded-md transition-colors font-medium"
				>
					Generate Commentary
				</button>
			{/if}
		</div>
	{/if}
</div>
