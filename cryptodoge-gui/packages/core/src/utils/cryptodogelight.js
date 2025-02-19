import Big from 'big.js';
import units from './units';

// TODO: use bigint instead of float
const convert = (amount, from, to) => {
  if (Number.isNaN(Number.parseFloat(amount)) || !Number.isFinite(amount)) {
    return 0;
  }

  const amountInFromUnit = Big(amount).times(units.getUnit(from));

  return Number.parseFloat(amountInFromUnit.div(units.getUnit(to)));
};

class Cryptodoge {
  constructor(value, unit) {
    this._value = value;
    this._unit = unit;
  }

  to(newUnit) {
    this._value = convert(this._value, this._unit, newUnit);
    this._unit = newUnit;

    return this;
  }

  value() {
    return this._value;
  }

  format() {
    const displayUnit = units.getDisplay(this._unit);

    const { format, fractionDigits, trailing } = displayUnit;

    let options = { maximumFractionDigits: fractionDigits };

    if (trailing) {
      options = { minimumFractionDigits: fractionDigits };
    }

    let value;

    if (fractionDigits !== undefined) {
      const fractionPower = Big(10).pow(fractionDigits);
      value = Number.parseFloat(
        Big(Math.floor(Big(this._value).times(fractionPower))).div(
          fractionPower,
        ),
      );
    } else {
      value = this._value;
    }

    let formatted = format.replace(
      '{amount}',
      Number.parseFloat(value).toLocaleString(undefined, options),
    );

    if (displayUnit.pluralize && this._value !== 1) {
      formatted += 's';
    }

    return formatted;
  }

  toString() {
    const displayUnit = units.getDisplay(this._unit);
    const { fractionDigits } = displayUnit;
    const options = { maximumFractionDigits: fractionDigits };
    return Number.parseFloat(this._value).toLocaleString(undefined, options);
  }
}

export const cryptodogelight_formatter = (value, unit) => new Cryptodoge(value, unit);

cryptodogelight_formatter.convert = convert;
cryptodogelight_formatter.setDisplay = units.setDisplay;
cryptodogelight_formatter.setUnit = units.setUnit;
cryptodogelight_formatter.getUnit = units.getUnit;
cryptodogelight_formatter.setFiat = (currency, rate, display = null) => {
  units.setUnit(currency, 1 / rate, display);
};

export const mojo_to_cryptodogelight = (mojo) => {
  return cryptodogelight_formatter(Number.parseInt(mojo), 'mojo').to('cryptodogelight').value();
};

export const cryptodogelight_to_mojo = (cryptodogelight) => {
  return cryptodogelight_formatter(Number.parseFloat(Number(cryptodogelight)), 'cryptodogelight')
    .to('mojo')
    .value();
};

export const mojo_to_cryptodogelight_string = (mojo) => {
  return cryptodogelight_formatter(Number(mojo), 'mojo').to('cryptodogelight').toString();
};

export const mojo_to_colouredcoin = (mojo) => {
  return cryptodogelight_formatter(Number.parseInt(mojo), 'mojo')
    .to('colouredcoin')
    .value();
};

export const colouredcoin_to_mojo = (colouredcoin) => {
  return cryptodogelight_formatter(Number.parseFloat(Number(colouredcoin)), 'colouredcoin')
    .to('mojo')
    .value();
};

export const mojo_to_colouredcoin_string = (mojo) => {
  return cryptodogelight_formatter(Number(mojo), 'mojo').to('colouredcoin').toString();
};
