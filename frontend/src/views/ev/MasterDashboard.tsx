import { EvCalculator } from './EvCalculator';
import { KellySizer } from './KellySizer';
import { BayesianUpdater } from './BayesianUpdater';
import { TradeSetup } from './TradeSetup';
import { FundingAnalyzer } from './FundingAnalyzer';
import { LiqMap } from './LiqMap';
import { OnChainSignals } from './OnChainSignals';
import { BacktestValidator } from './BacktestValidator';
import { CalibrationTracker } from './CalibrationTracker';

export const MasterDashboard: React.FC = () => {
    return (
        <div style={{ padding: '2rem' }}>
            <h1 style={{ marginBottom: '0.5rem', textAlign: 'center', fontSize: '2.5rem', color: 'var(--text-color)' }}>
                EV_MASTER_HUB
            </h1>
            <p style={{ textAlign: 'center', color: 'var(--text-muted)', marginBottom: '3rem' }}>
                Unified Quantitative Pre-Trade Intelligence & Risk Distribution
            </p>

            {/* Strategic High-Level Verdicts */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(450px, 1fr))', gap: '2rem', marginBottom: '4rem' }}>
                <TradeSetup />
                <BacktestValidator />
            </div>

            {/* Core Probability & Sizing Foundation */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(400px, 1fr))', gap: '2rem', marginBottom: '4rem' }}>
                <EvCalculator />
                <KellySizer />
            </div>

            {/* Market Context & Feed Aggregation */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(350px, 1fr))', gap: '2rem', marginBottom: '4rem' }}>
                <LiqMap />
                <OnChainSignals />
                <FundingAnalyzer />
            </div>

            {/* Belief Refinement & Accuracy Tracking */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(450px, 1fr))', gap: '2rem' }}>
                <BayesianUpdater />
                <CalibrationTracker />
            </div>
        </div>
    );
};
