import React from 'react';
import { Trans } from '@lingui/macro';
import { useGetWalletsQuery } from '@cryptodogelight/api-react';
import StandardWallet from './standard/WalletStandard';
import { CreateWalletView } from './create/WalletCreate';
import WalletCAT from './cat/WalletCAT';
// import RateLimitedWallet from './rateLimited/WalletRateLimited';
// import DistributedWallet from './did/WalletDID';
import WalletType from '../../constants/WalletType';
import LayoutMain from '../layout/LayoutMain';
import { Switch, Route, useRouteMatch } from 'react-router-dom';
import WalletsList from './WalletsList';

export default function Wallets() {
  const { path } = useRouteMatch();
  const { data: wallets, isLoading } = useGetWalletsQuery();

  return (
    <LayoutMain
      loading={isLoading}
      loadingTitle={<Trans>Loading list of wallets</Trans>}
      title={<Trans>Wallets</Trans>}
    >
      <Switch>
        <Route path="/dashboard/wallets" exact>
          <WalletsList />
        </Route>
        {wallets?.map((wallet) => (
          <Route path={`${path}/${wallet.id}`} key={wallet.id}>
            {wallet.type === WalletType.STANDARD_WALLET && (
              <StandardWallet walletId={wallet.id} />
            )}

            {wallet.type === WalletType.CAT && (
              <WalletCAT walletId={wallet.id} />
            )}

            {/* wallet.type === WalletType.RATE_LIMITED && (
              <RateLimitedWallet wallet_id={wallet.id} />
            ) */}

            {/* wallet.type === WalletType.DISTRIBUTED_ID && (
              <DistributedWallet walletId={wallet.id} />
            ) */}
          </Route>
        ))}
        <Route path={`/dashboard/wallets/create`}>
          <CreateWalletView />
        </Route>
      </Switch>
    </LayoutMain>
  );
}
