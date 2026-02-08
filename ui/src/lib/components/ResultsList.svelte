<script lang="ts">
	import { searchResults, searchQuery } from '$lib/stores/search';
	import { selectedVerse, selectVerse, hasSelection } from '$lib/stores/selection';
	import { BookOpen, Star } from 'lucide-svelte';
	import type { BibleSearchResult } from '$lib/types/bible';

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

	function truncateText(text: string, maxLength: number = 80): string {
		if (text.length <= maxLength) return text;
		return text.slice(0, maxLength) + '...';
	}
</script>

<div class="results-list h-full flex flex-col bg-gray-50 border-r border-gray-200">
	<!-- Header -->
	<div class="px-4 py-3 bg-white border-b border-gray-200">
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
						class="w-full text-left px-4 py-3 hover:bg-white transition-colors
							   {$selectedVerse?.chunk_id === result.chunk_id
								? 'bg-primary-50 border-l-4 border-primary-500'
								: 'bg-gray-50'}"
					>
						<!-- Reference and score -->
						<div class="flex items-start justify-between gap-2 mb-1">
							<span class="text-sm font-semibold text-gray-900">
								{result.verse_ref}
							</span>
							<span class="flex items-center gap-1 text-xs {getScoreColor(result.similarity)}">
								<Star class="h-3 w-3 fill-current" />
								{formatScore(result.similarity)}
							</span>
						</div>

						<!-- Translation -->
						<div class="text-xs text-gray-500 uppercase mb-2">
							{result.translation}
						</div>

						<!-- Preview text -->
						<p class="text-sm text-gray-700 leading-relaxed">
							{truncateText(result.text)}
						</p>
					</button>
				{/each}
			</div>
		{/if}
	</div>

	<!-- Footer hint -->
	{#if $searchResults.length > 0}
		<div class="px-4 py-2 bg-gray-100 border-t border-gray-200">
			<p class="text-xs text-gray-500 text-center">
				Click a verse to view translations and AI insights
			</p>
		</div>
	{/if}
</div>

<style>
	.results-list {
		min-width: 280px;
		max-width: 320px;
	}
</style>
