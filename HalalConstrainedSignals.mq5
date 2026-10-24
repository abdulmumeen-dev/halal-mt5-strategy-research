//+------------------------------------------------------------------+
//| HalalConstrainedSignals.mq5                                     |
//| Signal-only MT5 Expert Advisor                                  |
//| This file intentionally never submits, modifies, or cancels     |
//| broker orders. It produces alerts for independent review only.   |
//+------------------------------------------------------------------+
#property strict
#property version   "1.00"
#property description "Signal-only EMA/ATR/ADX research EA; no trade execution."

input int FastEMA = 20;
input int SlowEMA = 50;
input int ATRPeriod = 14;
input int ADXPeriod = 14;
input double MinADX = 18.0;
input double ATRStopMultiple = 1.8;
input double RewardRisk = 1.5;
input int MaxBarsInTrade = 12;
input int SessionStartUTC = 7;
input int SessionEndUTC = 16;
input int FlatBeforeCloseMinutes = 30;
input bool EnableAlerts = true;

int fastHandle, slowHandle, atrHandle, adxHandle;
datetime lastBar = 0;

int OnInit()
{
   fastHandle = iMA(_Symbol, _Period, FastEMA, 0, MODE_EMA, PRICE_CLOSE);
   slowHandle = iMA(_Symbol, _Period, SlowEMA, 0, MODE_EMA, PRICE_CLOSE);
   atrHandle  = iATR(_Symbol, _Period, ATRPeriod);
   adxHandle  = iADX(_Symbol, _Period, ADXPeriod);
   if(fastHandle == INVALID_HANDLE || slowHandle == INVALID_HANDLE || atrHandle == INVALID_HANDLE || adxHandle == INVALID_HANDLE)
      return INIT_FAILED;
   Comment("Halal-constrained SIGNAL ONLY\nNo orders will be sent.");
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
   IndicatorRelease(fastHandle);
   IndicatorRelease(slowHandle);
   IndicatorRelease(atrHandle);
   IndicatorRelease(adxHandle);
   Comment("");
}

bool InSession(datetime t)
{
   MqlDateTime dt;
   TimeToStruct(t, dt);
   return (dt.hour >= SessionStartUTC && dt.hour < SessionEndUTC);
}

bool NearSessionClose(datetime t)
{
   MqlDateTime dt;
   TimeToStruct(t, dt);
   int minutes = dt.hour * 60 + dt.min;
   int closeMinutes = SessionEndUTC * 60;
   return minutes >= closeMinutes - FlatBeforeCloseMinutes;
}

void OnTick()
{
   MqlRates rates[3];
   ArraySetAsSeries(rates, true);
   if(CopyRates(_Symbol, _Period, 0, 3, rates) != 3) return;
   if(rates[1].time == lastBar) return;
   lastBar = rates[1].time;

   double fast[3], slow[3], atr[3], adx[3];
   ArraySetAsSeries(fast, true); ArraySetAsSeries(slow, true);
   ArraySetAsSeries(atr, true); ArraySetAsSeries(adx, true);
   if(CopyBuffer(fastHandle, 0, 0, 3, fast) != 3) return;
   if(CopyBuffer(slowHandle, 0, 0, 3, slow) != 3) return;
   if(CopyBuffer(atrHandle, 0, 0, 3, atr) != 3) return;
   if(CopyBuffer(adxHandle, 0, 0, 3, adx) != 3) return;

   string status = "Signal-only | no broker action";
   if(!InSession(rates[1].time) || NearSessionClose(rates[1].time))
   {
      Comment(status, "\nOutside allowed entry window / near session close.");
      return;
   }
   if(adx[1] < MinADX || atr[1] <= 0)
   {
      Comment(status, "\nNo signal: trend-strength or volatility filter failed.");
      return;
   }

   bool longSignal = fast[2] <= slow[2] && fast[1] > slow[1];
   bool shortSignal = fast[2] >= slow[2] && fast[1] < slow[1];
   if(!longSignal && !shortSignal)
   {
      Comment(status, "\nNo new crossover.");
      return;
   }

   double entry = rates[1].close;
   double stopDistance = atr[1] * ATRStopMultiple;
   double stop = longSignal ? entry - stopDistance : entry + stopDistance;
   double target = longSignal ? entry + stopDistance * RewardRisk : entry - stopDistance * RewardRisk;
   string side = longSignal ? "LONG" : "SHORT";
   string message = StringFormat("%s %s signal | entry %.5f | stop %.5f | target %.5f | ADX %.2f | ATR %.5f | expiry %d bars | SIGNAL ONLY", _Symbol, side, entry, stop, target, adx[1], atr[1], MaxBarsInTrade);
   Comment(message, "\nReview manually. No order was sent.");
   if(EnableAlerts) Alert(message);
}
