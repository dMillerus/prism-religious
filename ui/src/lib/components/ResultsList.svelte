<script lang="ts">
	import { searchResults, searchQuery } from '$lib/stores/search';
	import { selectedVerse, selectVerse, hasSelection } from '$lib/stores/selection';
	import { BookOpen, Star, MapPin, Languages } from 'lucide-svelte';
	import type { BibleSearchResult } from '$lib/types/bible';
	import { getTestament, OT_BOOKS, NT_BOOKS } from '$lib/api/sword';
	import { goto } from '$app/navigation';

	let showScores = false;

	function handleSelect(result: BibleSearchResult) {
		selectVerse(result);
	}

	function formatScore(score: number): string {
		return (score * 100).toFixed(0);
	}

	function getScoreColor(score: number): string {
		if (score >= 0.9) return 'text-green-600';
		if (score >= 0.8) return 'text-blue-600';
		if (score >= 0.7) return 'text-yellow-600';
		return 'text-gray-600';
	}

	function truncateText(text: string, maxLength: number = 120): string {
		if (text.length <= maxLength) return text;

		// Try sentence boundary first (. ! ?)
		const sentenceEnd = text.slice(0, maxLength).lastIndexOf('.');
		if (sentenceEnd > maxLength * 0.6) {
			return text.slice(0, sentenceEnd + 1);
		}

		// Try phrase boundary (, ; :)
		const lastComma = text.slice(0, maxLength).lastIndexOf(',');
		if (lastComma > maxLength * 0.6) {
			return text.slice(0, lastComma + 1) + '...';
		}

		// Fall back to word boundary
		const lastSpace = text.lastIndexOf(' ', maxLength);
		return text.slice(0, lastSpace > 0 ? lastSpace : maxLength) + '...';
	}

	// Check if verse has geography data (places mentioned)
	function hasGeographyData(result: BibleSearchResult): boolean {
		// Common biblical place keywords (simplified detection)
		const placeKeywords = [
			'Jerusalem', 'Bethlehem', 'Nazareth', 'Galilee', 'Jordan', 'Egypt',
			'Babylon', 'Damascus', 'Samaria', 'Judea', 'Israel', 'Canaan',
			'mountain', 'river', 'city', 'temple', 'sea', 'desert', 'wilderness'
		];

		const text = result.text.toLowerCase();
		return placeKeywords.some(keyword => text.includes(keyword.toLowerCase()));
	}

	// Check if verse has original language text available
	function hasOriginalLanguage(result: BibleSearchResult): boolean {
		const testament = getTestament(result.book);
		return testament !== null; // Both OT (Hebrew) and NT (Greek) available
	}

	// Get original language label
	function getOriginalLanguageLabel(result: BibleSearchResult): string {
		const testament = getTestament(result.book);
		return testament === 'OT' ? 'Hebrew' : 'Greek';
	}

	// Navigate to geography page with search
	function viewOnMap(result: BibleSearchResult, event: Event) {
		event.stopPropagation();
		goto(`/geography?search=${encodeURIComponent(result.verse_ref)}`);
	}

	// Navigate to languages page with verse
	function viewInOriginal(result: BibleSearchResult, event: Event) {
		event.stopPropagation();
		const params = new URLSearchParams({
			book: result.book,
			chapter: result.chapter.toString(),
			verse: result.verse.toString()
		});
		goto(`/languages?${params.toString()}`);
	}
</script>

<div class="results-list h-full flex flex-col bg-gray-50 border-r border-gray-200">
	<!-- Header -->
	<div class="px-4 py-3 bg-white border-b border-gray-200">
		<div class="flex items-start justify-between">
			<div>
				<h2 class="text-sm font-semibold text-gray-700 flex items-center gap-2">
					<BookOpen class="h-4 w-4" />
					Results
					{#if $searchResults.length > 0}
						<span class="text-xs font-normal text-gray-500">
							({$searchResults.length})
						</span>
					{/if}
				</h2>
				{#if $searchQuery}
					<p class="text-xs text-gray-500 mt-1 truncate">
						Search: "{$searchQuery}"
					</p>
				{/if}
			</div>
			{#if $searchResults.length > 0}
				<button
					on:click={() => showScores = !showScores}
					class="text-xs text-gray-500 hover:text-gray-700 flex items-center gap-1 transition-colors"
					title="Toggle similarity scores">
					<Star class="h-3 w-3" />
					{showScores ? 'Hide' : 'Show'}
				</button>
			{/if}
		</div>
	</div>

	<!-- Results list -->
	<div class="flex-1 overflow-y-auto">
		{#if $searchResults.length === 0 && $searchQuery}
			<div class="px-4 py-8 text-center text-gray-500">
				<BookOpen class="h-12 w-12 mx-auto mb-3 opacity-30" />
				<p class="text-sm">No results found</p>
				<p class="text-xs mt-1">Try a different search query</p>
			</div>
		{:else if $searchResults.length === 0}
			<div class="px-4 py-8 text-center text-gray-500">
				<BookOpen class="h-12 w-12 mx-auto mb-3 opacity-30" />
				<p class="text-sm">Search the Bible</p>
				<p class="text-xs mt-1">Enter a query above to begin</p>
			</div>
		{:else}
			<div class="divide-y divide-gray-200">
				{#each $searchResults as result}
					<button
						on:click={() => handleSelect(result)}
						class="w-full text-left px-5 py-4 hover:bg-white transition-all duration-150
							   {$selectedVerse?.chunk_id === result.chunk_id
								? 'bg-white border-l-4 border-primary-500 shadow-md ring-1 ring-primary-200'
								: 'bg-gray-50'}"
					>
						<!-- Reference and score -->
						<div class="flex items-start justify-between gap-2 mb-2">
							<div class="flex items-center gap-2">
								<span class="text-lg font-bold text-gray-900">
									{result.verse_ref}
								</span>
								<!-- Feature indicators -->
								<div class="flex items-center gap-1">
									{#if hasGeographyData(result)}
										<span
											class="text-olive-600 hover:text-olive-800"
											title="Place mentioned - view on map"
										>
											<MapPin class="h-3 w-3" />
										</span>
									{/if}
									{#if hasOriginalLanguage(result)}
										<span
											class="text-primary-600 hover:text-primary-800"
											title="{getOriginalLanguageLabel(result)} text available"
										>
											<Languages class="h-3 w-3" />
										</span>
									{/if}
								</div>
							</div>
							{#if showScores}
								<span class="flex items-center gap-1 text-xs {getScoreColor(result.similarity)}">
									<Star class="h-3 w-3 fill-current" />
									{formatScore(result.similarity)}
								</span>
							{/if}
						</div>

						<!-- Translation -->
						<div class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-sm font-medium mb-3
							{result.translation === 'kjv' ? 'bg-indigo-100 text-indigo-800 border border-indigo-200' :
							 result.translation === 'asv' ? 'bg-olive-100 text-olive-800 border border-olive-200' :
							 result.translation === 'bbe' ? 'bg-primary-100 text-primary-800 border border-primary-200' :
							 result.translation === 'ylt' ? 'bg-sand-200 text-sand-900 border border-sand-300' :
							 'bg-gray-100 text-gray-800 border border-gray-200'}">
							<BookOpen class="h-3.5 w-3.5" />
							{result.translation.toUpperCase()}
						</div>

						<!-- Preview text -->
						<p class="text-base text-gray-700 leading-loose mb-2">
							{truncateText(result.text)}
						</p>

						<!-- Action buttons (shown on hover or selection) -->
						{#if $selectedVerse?.chunk_id === result.chunk_id}
							<div class="flex gap-2 mt-2 pt-2 border-t border-primary-200">
								{#if hasGeographyData(result)}
									<button
										on:click={(e) => viewOnMap(result, e)}
										class="flex items-center gap-1 px-2 py-1 bg-olive-100 hover:bg-olive-200 text-olive-800 rounded text-xs transition-colors"
										title="View places on map"
									>
										<MapPin class="h-3 w-3" />
										View on Map
									</button>
								{/if}
								{#if hasOriginalLanguage(result)}
									<button
										on:click={(e) => viewInOriginal(result, e)}
										class="flex items-center gap-1 px-2 py-1 bg-primary-100 hover:bg-primary-200 text-primary-800 rounded text-xs transition-colors"
										title="View {getOriginalLanguageLabel(result)} text"
									>
										<Languages class="h-3 w-3" />
										View in {getOriginalLanguageLabel(result)}
									</button>
								{/if}
							</div>
						{/if}
					</button>
				{/each}
			</div>
		{/if}
	</div>

	<!-- Footer hint with feature legend -->
	{#if $searchResults.length > 0}
		<div class="px-4 py-3 bg-sand-50 border-t border-sand-200">
			<p class="text-xs text-gray-600 text-center mb-2">
				Click a verse to view translations and AI insights
			</p>
			<div class="flex items-center justify-center gap-4 text-xs text-gray-500">
				<div class="flex items-center gap-1">
					<MapPin class="h-3 w-3 text-olive-600" />
					<span>Geography</span>
				</div>
				<div class="flex items-center gap-1">
					<Languages class="h-3 w-3 text-primary-600" />
					<span>Original Text</span>
				</div>
			</div>
		</div>
	{/if}
</div>

<style>
	.results-list {
		min-width: 280px;
		max-width: 320px;
	}

	/* Mobile responsive adjustments */
	@media (max-width: 767px) {
		.results-list {
			min-width: 100%;
			max-width: 100%;
		}
	}

	/* Tablet responsive adjustments */
	@media (min-width: 768px) and (max-width: 1023px) {
		.results-list {
			min-width: 260px;
			max-width: 280px;
		}
	}
</style>
