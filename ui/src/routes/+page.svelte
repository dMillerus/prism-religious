<script lang="ts">
	import { BookOpen, Settings, HelpCircle } from 'lucide-svelte';
	import SearchBar from '$lib/components/SearchBar.svelte';
	import ResultsList from '$lib/components/ResultsList.svelte';
	import TranslationGrid from '$lib/components/TranslationGrid.svelte';
	import AIPanel from '$lib/components/AIPanel.svelte';
</script>

<svelte:head>
	<title>Bible Study - Semantic Search & AI Insights</title>
</svelte:head>

<div class="app h-screen flex flex-col">
	<!-- Top navigation bar -->
	<nav class="bg-primary-700 text-white px-6 py-3 flex items-center justify-between shadow-md">
		<div class="flex items-center gap-3">
			<BookOpen class="h-6 w-6" />
			<h1 class="text-xl font-bold">Bible Study</h1>
			<span class="text-xs bg-primary-600 px-2 py-1 rounded">Beta</span>
		</div>

		<div class="flex items-center gap-4">
			<button
				class="text-sm hover:text-primary-100 transition-colors flex items-center gap-1"
				title="Help"
			>
				<HelpCircle class="h-4 w-4" />
				Help
			</button>
			<button
				class="text-sm hover:text-primary-100 transition-colors flex items-center gap-1"
				title="Settings"
			>
				<Settings class="h-4 w-4" />
				Settings
			</button>
		</div>
	</nav>

	<!-- Search bar -->
	<SearchBar />

	<!-- Main content area with 3-panel layout -->
	<div class="flex-1 flex overflow-hidden">
		<!-- Left panel: Results list -->
		<aside class="w-80 flex-shrink-0">
			<ResultsList />
		</aside>

		<!-- Center panel: Translation comparison -->
		<main class="flex-1 overflow-hidden">
			<TranslationGrid />
		</main>

		<!-- Right panel: AI insights -->
		<aside class="w-96 flex-shrink-0">
			<AIPanel />
		</aside>
	</div>

	<!-- Footer status bar -->
	<footer class="bg-gray-800 text-gray-400 px-6 py-2 text-xs flex items-center justify-between">
		<div class="flex items-center gap-4">
			<span>Powered by Prism + Ollama</span>
			<span class="text-gray-600">|</span>
			<span>5 translations • 18,069 verses indexed</span>
		</div>
		<div>
			<a href="https://github.com/anthropics/claude-code" target="_blank" class="hover:text-white transition-colors">
				Built with Claude Code
			</a>
		</div>
	</footer>
</div>

<style>
	.app {
		min-width: 1280px; /* Desktop-only design */
	}
</style>
