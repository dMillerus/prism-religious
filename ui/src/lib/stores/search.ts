// Search state management

import { writable, derived } from 'svelte/store';
import type { BibleSearchResult, SearchFilters, Translation } from '$lib/types/bible';

// Search query
export const searchQuery = writable<string>('');

// Search filters
export const searchFilters = writable<SearchFilters>({
	translations: ['kjv', 'asv', 'bbe', 'ylt', 'webster'],
	top_k: 20
});

// Search results
export const searchResults = writable<BibleSearchResult[]>([]);

// Loading state
export const isSearching = writable<boolean>(false);

// Error state
export const searchError = writable<string | null>(null);

// Derived: has active search
export const hasResults = derived(
	searchResults,
	($results) => $results.length > 0
);

// Derived: selected translations
export const selectedTranslations = derived(
	searchFilters,
	($filters) => $filters.translations
);

/**
 * Reset search state
 */
export function resetSearch() {
	searchQuery.set('');
	searchResults.set([]);
	searchError.set(null);
}

/**
 * Toggle translation in filter
 */
export function toggleTranslation(translation: Translation) {
	searchFilters.update(filters => {
		const translations = [...filters.translations];
		const index = translations.indexOf(translation);

		if (index > -1) {
			// Remove if present (but keep at least one)
			if (translations.length > 1) {
				translations.splice(index, 1);
			}
		} else {
			// Add if not present
			translations.push(translation);
		}

		return { ...filters, translations };
	});
}

/**
 * Set all translations
 */
export function setTranslations(translations: Translation[]) {
	searchFilters.update(filters => ({
		...filters,
		translations: translations.length > 0 ? translations : ['kjv']
	}));
}
