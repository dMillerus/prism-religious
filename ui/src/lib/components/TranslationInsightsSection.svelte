<script lang="ts">
	import { selectedVerse, comparisonData } from '$lib/stores/selection';
	import { getCached, setCached, translationInsightsKey } from '$lib/stores/cache';
	import { compareTranslations } from '$lib/api/ollama';
	import { ChevronDown, ChevronRight, Languages, RefreshCw } from 'lucide-svelte';

	let expanded = false;
	let loading = false;
	let insights: string | null = null;
	let error: string | null = null;

	$: if ($selectedVerse && expanded && !insights && Object.keys($comparisonData).length > 1) {
		loadInsights();
	}

	async function loadInsights() {
		if (!$selectedVerse || Object.keys($comparisonData).length < 2) return;

		const translations = Object.keys($comparisonData);
		const cacheKey = translationInsightsKey($selectedVerse.verse_ref, translations);

		// Check cache first
		const cached = getCached<string>(cacheKey);
		if (cached) {
			insights = cached;
			return;
		}

		loading = true;
		error = null;

		try {
			const result = await compareTranslations(
				$selectedVerse.verse_ref,
				$comparisonData
			);

			insights = result;
			setCached(cacheKey, result);
		} catch (err) {
			console.error('Translation insights generation failed:', err);
			error = 'Failed to generate translation insights. Please try again.';
		} finally {
			loading = false;
		}
	}

	function toggle() {
		expanded = !expanded;
	}

	// Reset when verse changes
	$: if ($selectedVerse) {
		insights = null;
		error = null;
		expanded = false;
	}
</script>

<div class="translation-insights-section bg-white rounded-lg border border-gray-200 overflow-hidden">
	<!-- Header -->
	<button
		on:click={toggle}
		class="w-full px-4 py-3 flex items-center justify-between hover:bg-gray-50 transition-colors"
	>
		<div class="flex items-center gap-2">
			<Languages class="h-4 w-4 text-primary-600" />
			<h3 class="text-sm font-semibold text-gray-800">Translation Differences</h3>
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
					Analyzing translations...
				</div>
			{:else if error}
				<div class="text-sm text-red-600 bg-red-50 border border-red-200 rounded p-2">
					{error}
					<button
						on:click={loadInsights}
						class="mt-2 text-red-700 hover:text-red-800 font-medium underline"
					>
						Retry
					</button>
				</div>
			{:else if insights}
				<div class="prose prose-sm max-w-none text-gray-700 leading-relaxed">
					{@html insights.replace(/\n\n/g, '</p><p class="mt-3">')}
				</div>
			{:else}
				<button
					on:click={loadInsights}
					class="w-full py-2 px-4 text-sm text-primary-700 bg-primary-50 hover:bg-primary-100
						   border border-primary-200 rounded-md transition-colors font-medium"
				>
					Analyze Translation Differences
				</button>
			{/if}
		</div>
	{/if}
</div>
