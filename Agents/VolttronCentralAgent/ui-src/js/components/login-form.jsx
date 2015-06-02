'use strict';

var React = require('react');
var Router = require('react-router');

var loginFormStore = require('../stores/login-form-store');
var platformManagerActionCreators = require('../action-creators/platform-manager-action-creators');

var LoginForm = React.createClass({
    mixins: [Router.Navigation],
    getInitialState: getStateFromStores,
    componentDidMount: function () {
        loginFormStore.addChangeListener(this._onStoresChange);
    },
    componentWillUnmount: function () {
        loginFormStore.removeChangeListener(this._onStoresChange);
    },
    _onStoresChange: function () {
        this.setState(getStateFromStores());
    },
    _onInputChange: function () {
        this.setState({
            username: this.refs.username.getDOMNode().value,
            password: this.refs.password.getDOMNode().value,
            error: null,
        });
    },
    _onSubmit: function (e) {
        e.preventDefault();
        platformManagerActionCreators.requestAuthorization(
            this.state.username,
            this.state.password
        );
        this.transitionTo('/');
    },
    render: function () {
        return (
            <form className="login-form" onSubmit={this._onSubmit}>
                <input
                    className="login-form__field"
                    ref="username"
                    type="text"
                    placeholder="Username"
                    autoFocus
                    onChange={this._onInputChange}
                />
                <input
                    className="login-form__field"
                    ref="password"
                    type="password"
                    placeholder="Password"
                    onChange={this._onInputChange}
                />
                <input
                    className="button login-form__submit"
                    type="submit"
                    value="Log in"
                    disabled={!this.state.username || !this.state.password}
                />
                {this.state.error ? (
                    <div className="error">
                        {this.state.error.message} ({this.state.error.code})
                    </div>
                ) : null }
            </form>
        );
    }
});

function getStateFromStores() {
    return { error: loginFormStore.getLastError() };
}

module.exports = LoginForm;