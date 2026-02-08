<script lang="ts">
	import { selectedVerse, comparisonData } from '$lib/stores/selection';
	import { Sparkles } from 'lucide-svelte';
	import CommentarySection from './CommentarySection.svelte';
	import CrossRefSection from './CrossRefSection.svelte';
	import TranslationInsightsSection from './TranslationInsightsSection.svelte';
</script>

<div class="ai-panel h-full flex flex-col bg-gray-50 border-l border-gray-200 overflow-y-auto">
	<!-- Header -->
	<div class="sticky top-0 z-10 px-4 py-3 bg-white border-b border-gray-200">
		<h2 class="text-sm font-semibold text-gray-700 flex items-center gap-2">
			<Sparkles class="h-4 w-4 text-primary-600" />
			AI Insights
		</h2>
	</div>

	{#if !$selectedVerse}
		<!-- Empty state -->
		<div class="flex-1 flex items-center justify-center p-6">
			<div class="text-center text-gray-400">
				<Sparkles class="h-12 w-12 mx-auto mb-3 opacity-30" />
				<p class="text-sm">AI-generated insights will appear here</p>
				<p class="text-xs mt-2">Select a verse to begin</p>
			</div>
		</div>
	{:else}
		<!-- AI sections -->
		<div class="flex-1 p-4 space-y-4">
			<!-- Commentary section -->
			<CommentarySection />

			<!-- Cross-references section -->
			<CrossRefSection />

			<!-- Translation insights section (only if comparing multiple translations) -->
			{#if Object.keys($comparisonData).length > 1}
				<TranslationInsightsSection />
			{/if}
		</div>

		<!-- Footer -->
		<div class="sticky bottom-0 px-4 py-3 bg-gray-100 border-t border-gray-200">
			<p class="text-xs text-gray-500 text-center">
				AI insights powered by Qwen 2.5
			</p>
		</div>
	{/if}
</div>

<style>
	.ai-panel {
		min-width: 320px;
		max-width: 400px;
	}
</style>
