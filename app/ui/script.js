document.addEventListener('DOMContentLoaded', function() {
    const sportFilter = document.getElementById('sportFilter');
    const refreshBtn = document.getElementById('refreshBtn');
    const betsContainer = document.getElementById('betsContainer');
    const legsContainer = document.getElementById('legsContainer');
    const lastUpdated = document.getElementById('lastUpdated');

    loadWeeklySummary();
    loadRecommendedLegs();

    sportFilter.addEventListener('change', filterLegs);
    refreshBtn.addEventListener('click', function() {
        loadWeeklySummary();
        loadRecommendedLegs();
    });

    let allLegs = [];

    function filterLegs() {
        const sport = sportFilter.value.toLowerCase();
        if (!sport) {
            renderLegs(allLegs);
        } else {
            renderLegs(allLegs.filter(leg => leg.sport.toLowerCase() === sport));
        }
    }

    async function loadWeeklySummary() {
        try {
            const response = await fetch('/weekly-summary');
            const data = await response.json();
            
            if (data.success) {
                document.getElementById('marketsAnalyzed').textContent = data.total_markets_analyzed || '-';
                document.getElementById('recommendedCount').textContent = data.recommended_legs_count || '-';
                document.getElementById('avgProbability').textContent = data.average_model_probability ? `${data.average_model_probability}%` : '-';
                document.getElementById('avgEV').textContent = data.average_ev ? `${data.average_ev > 0 ? '+' : ''}${data.average_ev}%` : '-';
                
                if (data.last_updated) {
                    lastUpdated.textContent = `Last updated: ${new Date(data.last_updated).toLocaleString()}`;
                }
            }
        } catch (error) {
            console.error('Error loading summary:', error);
        }
    }

    async function loadRecommendedLegs() {
        legsContainer.innerHTML = '<p class="loading">Loading recommended legs...</p>';
        
        try {
            const response = await fetch('/recommended-legs?limit=20');
            const data = await response.json();
            
            if (data.success && data.recommended_legs && data.recommended_legs.length > 0) {
                allLegs = data.recommended_legs;
                renderLegs(allLegs);
            } else {
                legsContainer.innerHTML = '<p class="loading">No recommended legs found in the 1.05-1.25 odds range.</p>';
            }
        } catch (error) {
            legsContainer.innerHTML = '<p class="error">Error loading recommended legs. Please try again.</p>';
            console.error('Error:', error);
        }
    }


    function renderLegs(legs) {
        legsContainer.innerHTML = `
            <div class="legs-cards-container">
                ${legs.map((leg, index) => `
                    <div class="leg-card ${leg.rivalry_flag ? 'rivalry-warning' : ''}" data-index="${index}">
                        <div class="leg-card-header">
                            <div class="leg-header-left">
                                <span class="leg-number">#${index + 1}</span>
                                <span class="sport-badge">${leg.sport.toUpperCase()}</span>
                                ${leg.rivalry_flag ? '<span class="rivalry-badge">Rivalry</span>' : ''}
                            </div>
                            <div class="leg-header-right">
                                <span class="confidence-badge ${(leg.confidence || 'medium').toLowerCase()}">${leg.confidence || 'MEDIUM'}</span>
                                <span class="composite-score">Score: ${leg.composite_score?.toFixed(1) || '-'}</span>
                            </div>
                        </div>
                        <div class="leg-card-body">
                            <div class="leg-event">${leg.event || '-'}</div>
                            <div class="leg-selection">${leg.selection}</div>
                            <div class="leg-stats">
                                <div class="stat-item">
                                    <span class="stat-label">Odds</span>
                                    <span class="stat-value odds">$${leg.decimal_odds?.toFixed(2) || '-'}</span>
                                </div>
                                <div class="stat-item">
                                    <span class="stat-label">Model %</span>
                                    <span class="stat-value">${leg.model_probability?.toFixed(1) || '-'}%</span>
                                </div>
                                <div class="stat-item">
                                    <span class="stat-label">Implied %</span>
                                    <span class="stat-value">${leg.implied_probability?.toFixed(1) || '-'}%</span>
                                </div>
                                <div class="stat-item">
                                    <span class="stat-label">EV</span>
                                    <span class="stat-value ${leg.expected_value > 0 ? 'positive' : 'negative'}">
                                        ${leg.expected_value > 0 ? '+' : ''}${leg.expected_value?.toFixed(1) || '-'}%
                                    </span>
                                </div>
                            </div>
                            ${leg.favorite_stats ? `
                                <div class="team-stats">
                                    <span class="stats-label">Form:</span>
                                    <span class="stats-value">Last 10: ${leg.favorite_stats.last_10 || 'N/A'}</span>
                                    <span class="stats-value">Diff: ${leg.favorite_stats.point_diff > 0 ? '+' : ''}${leg.favorite_stats.point_diff?.toFixed(1) || 'N/A'}</span>
                                </div>
                            ` : ''}
                        </div>
                        ${leg.rationale ? `
                            <div class="leg-rationale">
                                <div class="rationale-header" onclick="this.parentElement.classList.toggle('expanded')">
                                    <span>Why this pick?</span>
                                    <span class="expand-icon">+</span>
                                </div>
                                <div class="rationale-content">
                                    <p>${leg.rationale}</p>
                                </div>
                            </div>
                        ` : ''}
                    </div>
                `).join('')}
            </div>
            <div class="legs-footer">
                <p>These are high-confidence legs suitable for combining into a multi bet targeting ~$2.00 odds</p>
                <p class="tip">Tip: Select 3-4 legs from different sports to diversify your multi</p>
            </div>
        `;
    }

});

function toggleRationale(btn) {
    const popup = btn.nextElementSibling;
    const allPopups = document.querySelectorAll('.rationale-popup');
    allPopups.forEach(p => {
        if (p !== popup) p.classList.remove('visible');
    });
    popup.classList.toggle('visible');
}
