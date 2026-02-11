<script lang="ts">
	import { selectedVerse, compareTranslations, comparisonData } from '$lib/stores/selection';
	import { getVerseInTranslations } from '$lib/api/prism';
	import { BookMarked, RefreshCw, Copy, Check } from 'lucide-svelte';
	import type { Translation } from '$lib/types/bible';

	let loading = false;
	let error: string | null = null;
	let copied = false;

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

	async function copyCitation() {
		if (!$selectedVerse) return;

		const citation = `${$selectedVerse.verse_ref} (${$selectedVerse.translation.toUpperCase()})`;

		try {
			await navigator.clipboard.writeText(citation);
			copied = true;
			setTimeout(() => {
				copied = false;
			}, 2000);
		} catch (err) {
			console.error('Failed to copy citation:', err);
		}
	}

	function exportVerse() {
		if (!$selectedVerse || Object.keys($comparisonData).length === 0) return;

		const lines = [
			`Reference: ${$selectedVerse.verse_ref}`,
			'',
			'Translations:',
			''
		];

		Object.entries($comparisonData).forEach(([trans, text]) => {
			lines.push(`${trans.toUpperCase()}: ${text}`);
			lines.push('');
		});

		lines.push('');
		lines.push('---');
		lines.push(`Source: Prism Religious Studies (Christianity Module)`);
		lines.push(`Generated: ${new Date().toLocaleDateString()}`);

		const content = lines.join('\n');
		const blob = new Blob([content], { type: 'text/plain' });
		const url = URL.createObjectURL(blob);
		const a = document.createElement('a');
		a.href = url;
		a.download = `${$selectedVerse.verse_ref.replace(/\s+/g, '_')}.txt`;
		document.body.appendChild(a);
		a.click();
		document.body.removeChild(a);
		URL.revokeObjectURL(url);
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
		<div class="px-8 py-5 border-b border-gray-200 bg-gradient-to-r from-white to-sand-50">
			<div class="flex items-start justify-between">
				<div>
					<h2 class="text-xl font-bold text-gray-900 font-heading mb-1">
						{$selectedVerse.verse_ref}
					</h2>
					<p class="text-base text-gray-600">
						Translation Comparison ({$compareTranslations.length} versions)
					</p>
				</div>
				<!-- Citation and Export buttons -->
				<div class="flex gap-2">
					<button
						on:click={copyCitation}
						class="flex items-center gap-1 px-3 py-1.5 bg-sand-100 hover:bg-sand-200 text-gray-700 rounded text-xs transition-colors"
						title="Copy citation to clipboard"
					>
						{#if copied}
							<Check class="h-3 w-3 text-green-600" />
							<span class="text-green-600">Copied!</span>
						{:else}
							<Copy class="h-3 w-3" />
							<span>Copy Citation</span>
						{/if}
					</button>
					<button
						on:click={exportVerse}
						class="flex items-center gap-1 px-3 py-1.5 bg-primary-100 hover:bg-primary-200 text-primary-800 rounded text-xs transition-colors"
						title="Export verse to text file"
					>
						<BookMarked class="h-3 w-3" />
						<span>Export</span>
					</button>
				</div>
			</div>
		</div>

		<!-- Grid content -->
		<div class="flex-1 overflow-y-auto p-8">
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
				<div class="grid grid-cols-{$compareTranslations.length} gap-8">
					{#each $compareTranslations as translation}
						<div class="flex flex-col">
							<!-- Translation header -->
							<div class="mb-4 pb-3 border-b-2 border-gray-300">
								<h3 class="text-sm font-bold text-gray-900 uppercase tracking-wider mb-1">
									{translation}
								</h3>
								<p class="text-sm text-gray-600">
									{getTranslationLabel(translation).split('(')[1]?.replace(')', '')}
								</p>
							</div>

							<!-- Translation text -->
							<div class="flex-1">
								{#if $comparisonData[translation]}
									<p class="text-lg leading-loose text-gray-800 text-justify">
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
					<div class="grid grid-cols-2 gap-3 text-xs text-gray-600 mb-4">
						{#each $compareTranslations as translation}
							<div>
								<span class="font-semibold">{translation.toUpperCase()}:</span>
								{getTranslationLabel(translation)}
							</div>
						{/each}
					</div>

					<!-- Data Provenance -->
					<div class="bg-sand-50 rounded-lg p-3 border border-sand-200">
						<h5 class="text-xs font-semibold text-gray-800 mb-1">Data Provenance</h5>
						<p class="text-xs text-gray-600">
							<strong>Source:</strong> SWORD Project Bible modules (Public Domain)<br/>
							<strong>Search Engine:</strong> Prism (Personal Semantic Data Layer)<br/>
							<strong>Embedding Model:</strong> nomic-embed-text (768 dimensions)<br/>
							<strong>Database:</strong> PostgreSQL with pgvector extension
						</p>
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

	/* Mobile responsive: Force single column */
	@media (max-width: 767px) {
		.grid-cols-2,
		.grid-cols-3,
		.grid-cols-4 {
			grid-template-columns: repeat(1, minmax(0, 1fr)) !important;
		}
	}

	/* Tablet responsive: Max 2 columns */
	@media (min-width: 768px) and (max-width: 1023px) {
		.grid-cols-3,
		.grid-cols-4 {
			grid-template-columns: repeat(2, minmax(0, 1fr)) !important;
		}
	}

	/* Small desktop: Max 3 columns */
	@media (min-width: 1024px) and (max-width: 1279px) {
		.grid-cols-4 {
			grid-template-columns: repeat(3, minmax(0, 1fr)) !important;
		}
	}
</style>
