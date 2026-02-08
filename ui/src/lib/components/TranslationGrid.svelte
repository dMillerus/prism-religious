<script lang="ts">
	import { selectedVerse, compareTranslations, comparisonData } from '$lib/stores/selection';
	import { getVerseInTranslations } from '$lib/api/prism';
	import { BookMarked, RefreshCw } from 'lucide-svelte';
	import type { Translation } from '$lib/types/bible';

	let loading = false;
	let error: string | null = null;

	$: if ($selectedVerse && $compareTranslations.length > 0) {
		loadComparisons();
	}

	async function loadComparisons() {
		if (!$selectedVerse) return;

		loading = true;
		error = null;

		try {
			const data = await getVerseInTranslations(
				$selectedVerse.book,
				$selectedVerse.chapter,
				$selectedVerse.verse,
				$compareTranslations
			);

			comparisonData.set(data);
		} catch (err) {
			console.error('Failed to load translation comparisons:', err);
			error = 'Failed to load translations. Please try again.';
		} finally {
			loading = false;
		}
	}

	function getTranslationLabel(trans: Translation): string {
		const labels: Record<Translation, string> = {
			kjv: 'King James Version (1611)',
			asv: 'American Standard Version (1901)',
			bbe: 'Bible in Basic English (1965)',
			ylt: 'Young\'s Literal Translation (1862)',
			webster: 'Webster\'s Bible (1833)'
		};
		return labels[trans];
	}
</script>

<div class="translation-grid h-full flex flex-col bg-white">
	{#if !$selectedVerse}
		<!-- Empty state -->
		<div class="flex-1 flex items-center justify-center text-gray-400">
			<div class="text-center">
				<BookMarked class="h-16 w-16 mx-auto mb-4 opacity-30" />
				<p class="text-lg font-medium">No verse selected</p>
				<p class="text-sm mt-2">Select a verse from the results to view translations</p>
			</div>
		</div>
	{:else}
		<!-- Header -->
		<div class="px-6 py-4 border-b border-gray-200">
			<h2 class="text-lg font-semibold text-gray-900">
				{$selectedVerse.verse_ref}
			</h2>
			<p class="text-sm text-gray-600 mt-1">
				Translation Comparison
			</p>
		</div>

		<!-- Grid content -->
		<div class="flex-1 overflow-y-auto p-6">
			{#if loading}
				<div class="flex items-center justify-center h-full">
					<div class="text-center">
						<RefreshCw class="h-8 w-8 mx-auto mb-3 text-primary-600 animate-spin" />
						<p class="text-sm text-gray-600">Loading translations...</p>
					</div>
				</div>
			{:else if error}
				<div class="bg-red-50 border border-red-200 rounded-lg p-4">
					<p class="text-sm text-red-600">{error}</p>
					<button
						on:click={loadComparisons}
						class="mt-2 text-sm text-red-700 hover:text-red-800 font-medium"
					>
						Try again
					</button>
				</div>
			{:else if Object.keys($comparisonData).length > 0}
				<!-- Grid layout -->
				<div class="grid grid-cols-{$compareTranslations.length} gap-6">
					{#each $compareTranslations as translation}
						<div class="flex flex-col">
							<!-- Translation header -->
							<div class="mb-3 pb-2 border-b border-gray-200">
								<h3 class="text-xs font-semibold text-gray-900 uppercase tracking-wide">
									{translation}
								</h3>
								<p class="text-xs text-gray-500 mt-0.5">
									{getTranslationLabel(translation).split('(')[1]?.replace(')', '')}
								</p>
							</div>

							<!-- Translation text -->
							<div class="flex-1">
								{#if $comparisonData[translation]}
									<p class="text-base leading-relaxed text-gray-800">
										{$comparisonData[translation]}
									</p>
								{:else}
									<p class="text-sm text-gray-400 italic">
										Translation not available
									</p>
								{/if}
							</div>
						</div>
					{/each}
				</div>

				<!-- Translation info footer -->
				<div class="mt-8 pt-6 border-t border-gray-200">
					<h4 class="text-sm font-semibold text-gray-700 mb-2">
						About These Translations:
					</h4>
					<div class="grid grid-cols-2 gap-3 text-xs text-gray-600">
						{#each $compareTranslations as translation}
							<div>
								<span class="font-semibold">{translation.toUpperCase()}:</span>
								{getTranslationLabel(translation)}
							</div>
						{/each}
					</div>
				</div>
			{/if}
		</div>
	{/if}
</div>

<style>
	.translation-grid {
		min-height: 0; /* Enable flexbox scrolling */
	}

	/* Dynamic grid columns based on translation count */
	.grid-cols-1 {
		grid-template-columns: repeat(1, minmax(0, 1fr));
	}
	.grid-cols-2 {
		grid-template-columns: repeat(2, minmax(0, 1fr));
	}
	.grid-cols-3 {
		grid-template-columns: repeat(3, minmax(0, 1fr));
	}
	.grid-cols-4 {
		grid-template-columns: repeat(4, minmax(0, 1fr));
	}
</style>
