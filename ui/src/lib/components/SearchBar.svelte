<script lang="ts">
	import { searchQuery, searchFilters, isSearching, searchResults, searchError, toggleTranslation, selectedTranslations } from '$lib/stores/search';
	import { searchBible } from '$lib/api/prism';
	import { Search, X } from 'lucide-svelte';
	import type { Translation } from '$lib/types/bible';

	const TRANSLATIONS: { id: Translation; label: string; year: string }[] = [
		{ id: 'kjv', label: 'KJV', year: '1611' },
		{ id: 'asv', label: 'ASV', year: '1901' },
		{ id: 'bbe', label: 'BBE', year: '1965' },
		{ id: 'ylt', label: 'YLT', year: '1862' },
		{ id: 'webster', label: 'Webster', year: '1833' }
	];

	let query = '';
	let debounceTimer: ReturnType<typeof setTimeout>;

	// Subscribe to search query store
	searchQuery.subscribe(q => query = q);

	function handleInput(event: Event) {
		const target = event.target as HTMLInputElement;
		query = target.value;
		searchQuery.set(query);

		// Debounce search (wait 500ms after user stops typing)
		clearTimeout(debounceTimer);

		if (query.trim().length > 2) {
			debounceTimer = setTimeout(() => {
				performSearch();
			}, 500);
		} else {
			searchResults.set([]);
		}
	}

	async function performSearch() {
		if (query.trim().length < 3) {
			return;
		}

		isSearching.set(true);
		searchError.set(null);

		try {
			const results = await searchBible(
				query,
				$selectedTranslations,
				$searchFilters.top_k
			);

			searchResults.set(results);
		} catch (error) {
			console.error('Search failed:', error);
			searchError.set('Search failed. Please check that Prism is running.');
		} finally {
			isSearching.set(false);
		}
	}

	function handleSubmit(event: Event) {
		event.preventDefault();
		if (query.trim().length > 2) {
			performSearch();
		}
	}

	function clearSearch() {
		query = '';
		searchQuery.set('');
		searchResults.set([]);
		searchError.set(null);
	}

	function handleTranslationToggle(translation: Translation) {
		toggleTranslation(translation);
	}
</script>

<div class="search-bar bg-white border-b border-gray-200 p-4">
	<form on:submit={handleSubmit} class="space-y-3">
		<!-- Search input -->
		<div class="relative">
			<div class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
				<Search class="h-5 w-5 text-gray-400" />
			</div>

			<input
				type="text"
				value={query}
				on:input={handleInput}
				placeholder="Search the Bible (e.g., 'faith hope love', 'shepherd', 'John 3:16')..."
				class="block w-full pl-10 pr-10 py-3 border border-gray-300 rounded-lg
					   focus:ring-2 focus:ring-primary-500 focus:border-primary-500
					   text-base placeholder-gray-400"
			/>

			{#if query}
				<button
					type="button"
					on:click={clearSearch}
					class="absolute inset-y-0 right-0 pr-3 flex items-center"
				>
					<X class="h-5 w-5 text-gray-400 hover:text-gray-600" />
				</button>
			{/if}
		</div>

		<!-- Translation filters -->
		<div class="flex items-center gap-2 flex-wrap">
			<span class="text-sm font-medium text-gray-700">Translations:</span>

			{#each TRANSLATIONS as translation}
				<button
					type="button"
					on:click={() => handleTranslationToggle(translation.id)}
					class="px-3 py-1 text-sm rounded-md border transition-colors
						   {$selectedTranslations.includes(translation.id)
							? 'bg-primary-100 border-primary-500 text-primary-700'
							: 'bg-gray-50 border-gray-300 text-gray-600 hover:bg-gray-100'}"
				>
					{translation.label}
					<span class="text-xs opacity-70">({translation.year})</span>
				</button>
			{/each}

			<span class="text-xs text-gray-500 ml-2">
				{$selectedTranslations.length} selected
			</span>
		</div>

		<!-- Search status -->
		{#if $isSearching}
			<div class="text-sm text-gray-600 flex items-center gap-2">
				<div class="animate-spin rounded-full h-4 w-4 border-b-2 border-primary-600"></div>
				Searching...
			</div>
		{/if}

		{#if $searchError}
			<div class="text-sm text-red-600 bg-red-50 border border-red-200 rounded-md p-2">
				{$searchError}
			</div>
		{/if}
	</form>
</div>

<style>
	/* Component-specific styles */
	.search-bar {
		min-height: fit-content;
	}
</style>
